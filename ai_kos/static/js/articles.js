// Column-header sorting + multi-filter for articles page
(function() {
  const tbody = document.querySelector('#article-table tbody');
  if (!tbody) return;

  const rows = Array.from(tbody.querySelectorAll('tr'));
  let currentSort = { key: 'title', asc: true };

  function sortVal(row, key) {
    const v = row.dataset[key];
    if (!v && key !== 'title') return '\uffff';
    if (key === 'reads' || key === 'links') return parseInt(v) || 0;
    if (key === 'updated' || key === 'created' || key === 'review') return v || '9999-99-99';
    return v || '';
  }

  function doSort(rowsToSort, key, asc) {
    return [...rowsToSort].sort((a, b) => {
      const va = sortVal(a, key), vb = sortVal(b, key);
      let cmp;
      if (typeof va === 'number') cmp = va - vb;
      else cmp = va.toString().localeCompare(vb.toString());
      return asc ? cmp : -cmp;
    });
  }

  function updateHeaders(key, asc) {
    document.querySelectorAll('#article-table th[data-sort]').forEach(th => {
      th.classList.remove('sorted');
      const ind = th.querySelector('.sort-indicator');
      if (ind) ind.textContent = '▲';
    });
    const active = document.querySelector(`#article-table th[data-sort="${key}"]`);
    if (active) {
      active.classList.add('sorted');
      const ind = active.querySelector('.sort-indicator');
      if (ind) ind.textContent = asc ? '▲' : '▼';
    }
  }

  function filterAndSort() {
    const query = document.getElementById('search').value.toLowerCase().trim();
    const type = document.getElementById('type-filter').value;
    const lifecycle = document.getElementById('lifecycle-filter').value;
    const doc = document.getElementById('doc-filter').value;

    let visible = rows.filter(row => {
      if (type && row.dataset.type !== type) return false;
      if (lifecycle && row.dataset.lifecycle !== lifecycle) return false;
      if (doc && row.dataset.doc !== doc) return false;
      if (query && !(row.dataset.title + ' ' + row.dataset.slug + ' ' + row.dataset.keywords).toLowerCase().includes(query)) return false;
      return true;
    });

    visible = doSort(visible, currentSort.key, currentSort.asc);

    tbody.innerHTML = '';
    if (visible.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="7" style="text-align:center;color:var(--text-dim);padding:32px">No articles match</td>';
      tbody.appendChild(tr);
    } else {
      visible.forEach(r => tbody.appendChild(r));
    }

    updateHeaders(currentSort.key, currentSort.asc);
  }

  // Click column headers to sort
  document.querySelectorAll('#article-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (currentSort.key === key) {
        currentSort.asc = !currentSort.asc;
      } else {
        currentSort.key = key;
        currentSort.asc = true;
      }
      filterAndSort();
    });
  });

  // Filter changes
  document.getElementById('search').addEventListener('input', filterAndSort);
  document.getElementById('type-filter').addEventListener('change', filterAndSort);
  document.getElementById('lifecycle-filter').addEventListener('change', filterAndSort);
  document.getElementById('doc-filter').addEventListener('change', filterAndSort);
})();
