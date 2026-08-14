-- Bird database schema + data dump
CREATE TABLE IF NOT EXISTS birds (
    id INTEGER PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    common_name TEXT,
    family TEXT,
    population INTEGER,
    conservation_status TEXT
);

INSERT INTO birds VALUES
(1, 'Corvus corax', 'Common Raven', 'Corvidae', 16000000, 'LC'),
(2, 'Haliaeetus leucocephalus', 'Bald Eagle', 'Accipitridae', 316700, 'LC'),
(3, 'Strix aluco', 'Tawny Owl', 'Strigidae', 1500000, 'LC'),
(4, 'Pica pica', 'Eurasian Magpie', 'Corvidae', 75000000, 'LC'),
(5, 'Turdus merula', 'Common Blackbird', 'Turdidae', 250000000, 'LC');

CREATE TABLE IF NOT EXISTS sightings (
    id INTEGER PRIMARY KEY,
    bird_id INTEGER REFERENCES birds(id),
    location TEXT,
    date TEXT,
    count INTEGER
);

INSERT INTO sightings VALUES
(1, 1, 'London, UK', '2024-03-15', 3),
(2, 2, 'Seattle, WA', '2024-04-02', 1),
(3, 3, 'Berlin, Germany', '2024-05-20', 2),
(4, 1, 'Edinburgh, UK', '2024-06-10', 5),
(5, 4, 'Paris, France', '2024-07-01', 12);
