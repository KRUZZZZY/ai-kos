"""AI-KOS article store — CRUD for knowledge articles + auto-linking on write."""

import os, uuid, logging, yaml
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, List

from ai_kos.schemas import ArticleType, ARTICLE_CLASSES, TEMPLATES, article_to_markdown
from ai_kos.config import get

logger = logging.getLogger("ai-kos.articles")
KNOWLEDGE_DIR = get("paths", "knowledge_dir", default="knowledge")


def _slug_path(slug: str) -> str:
    for md in Path(KNOWLEDGE_DIR).rglob(f"{slug}.md"):
        return str(md)
    return str(Path(KNOWLEDGE_DIR) / "bundles" / "general" / f"{slug}.md")


def create_article(article_type: str, data: dict) -> dict:
    cls = ARTICLE_CLASSES.get(ArticleType(article_type))
    if not cls:
        return {"error": f"Unknown article type: {article_type}"}
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
    today = date.today()
    for k in ['created_at','updated_at','reviewed_at']:
        data.setdefault(k, today)
    data.setdefault('next_review_at', today.replace(year=today.year + 1))
    try:
        article = cls(**data)
    except Exception as e:
        return {"error": f"Validation failed: {e}"}
    md_content = article_to_markdown(article)
    filepath = _slug_path(article.slug)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(md_content)
    logger.info(f"Created {article_type}: {article.slug}")
    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {"status":"created","slug":article.slug,"type":article_type,"filepath":filepath,"keywords":article.keywords,"linking":link_result}


def read_article(slug: str) -> dict | None:
    filepath = _slug_path(slug)
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        content = f.read()
    if not content.startswith('---'):
        return {"slug":slug,"error":"No frontmatter"}
    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ""
    return {"slug":slug,"filepath":filepath,"frontmatter":fm,"body":body.strip(),"raw":content}


def update_article(slug: str, updates: dict) -> dict:
    filepath = _slug_path(slug)
    if not os.path.exists(filepath):
        return {"error": f"Article not found: {slug}"}
    with open(filepath) as f:
        content = f.read()
    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    fm.update(updates)
    fm['updated_at'] = date.today().isoformat()
    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    body = parts[2] if len(parts) > 2 else ""
    with open(filepath, 'w') as f:
        f.write(f"---\n{new_fm}\n---{body}")
    from ai_kos.linker import link_all
    link_result = link_all(KNOWLEDGE_DIR)
    return {"status":"updated","slug":slug,"linking":link_result}


def delete_article(slug: str) -> dict:
    import shutil
    filepath = _slug_path(slug)
    if not os.path.exists(filepath):
        return {"error": f"Article not found: {slug}"}
    archive_dir = Path(get("paths","archive_dir",default="archive"))
    archive_dir.mkdir(exist_ok=True)
    dest = archive_dir / Path(filepath).name
    shutil.move(filepath, str(dest))
    logger.info(f"Deleted {slug} → {dest}")
    from ai_kos.linker import link_all
    link_all(KNOWLEDGE_DIR)
    return {"status":"deleted","slug":slug,"moved_to":str(dest)}


def list_articles(article_type: Optional[str] = None, keyword: Optional[str] = None) -> List[dict]:
    results = []
    for md in Path(KNOWLEDGE_DIR).rglob("*.md"):
        try:
            with open(md) as f:
                content = f.read()
            if not content.startswith('---'): continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            if article_type and fm.get('type') != article_type: continue
            if keyword and keyword.lower() not in [k.lower() for k in fm.get('keywords',[])]: continue
            results.append({"slug":fm.get('slug',md.stem),"title":fm.get('title',md.stem),"type":fm.get('type',''),"keywords":fm.get('keywords',[]),"summary":fm.get('summary',''),"related":fm.get('related',[]),"filepath":str(md)})
        except: continue
    return sorted(results, key=lambda r: r['title'])


def find_merge_candidates(slug: str) -> List[dict]:
    target_path = _slug_path(slug)
    if not os.path.exists(target_path): return []
    with open(target_path) as f:
        fm = yaml.safe_load(f.read().split('---')[1]) or {}
    target_kw = set(fm.get('keywords',[]))
    if not target_kw: return []
    candidates = []
    for md in Path(KNOWLEDGE_DIR).rglob("*.md"):
        if str(md) == target_path: continue
        try:
            with open(md) as f:
                fm2 = yaml.safe_load(f.read().split('---')[1]) or {}
            other_kw = set(fm2.get('keywords',[]))
            if not other_kw: continue
            overlap = target_kw & other_kw
            ratio = len(overlap) / min(len(target_kw), len(other_kw))
            if ratio > 0.5:
                candidates.append({"slug":fm2.get('slug',md.stem),"title":fm2.get('title',''),"shared_keywords":sorted(overlap),"overlap_ratio":round(ratio,2)})
        except: continue
    return sorted(candidates, key=lambda c: c['overlap_ratio'], reverse=True)


def stats() -> dict:
    articles = list_articles()
    by_type, by_stability = {}, {}
    buckets = {"0.0-0.3":0,"0.3-0.6":0,"0.6-0.8":0,"0.8-1.0":0}
    past_review, gaps = [], []
    total_kw, total_links = 0, 0

    for md in Path(KNOWLEDGE_DIR).rglob("*.md"):
        try:
            with open(md) as f: content = f.read()
            if not content.startswith('---'): continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            t = fm.get('type','unknown'); by_type[t] = by_type.get(t,0) + 1
            s = fm.get('stability','moderate'); by_stability[s] = by_stability.get(s,0) + 1
            c = fm.get('confidence',0.5)
            if c<0.3: buckets["0.0-0.3"]+=1
            elif c<0.6: buckets["0.3-0.6"]+=1
            elif c<0.8: buckets["0.6-0.8"]+=1
            else: buckets["0.8-1.0"]+=1
            try:
                nr = date.fromisoformat(str(fm.get('next_review_at','2099-01-01')))
                if nr < date.today(): past_review.append(fm.get('slug',md.stem))
            except: pass
            if fm.get('gap'): gaps.append(fm.get('slug',md.stem))
            total_kw += len(fm.get('keywords',[]))
            total_links += len(fm.get('related',[]))
        except: continue

    orphans = [a['slug'] for a in articles if not a['related']]
    n = max(1, len(articles))
    return {"total_articles":len(articles),"by_type":by_type,"by_stability":by_stability,"confidence_distribution":buckets,"articles_past_review":past_review,"gap_articles":gaps,"orphans":orphans,"total_keywords":total_kw,"total_links":total_links,"avg_keywords":round(total_kw/n,1),"avg_links":round(total_links/n,1)}
