-- PostGIS spatial data sample
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS bird_sightings (
    id SERIAL PRIMARY KEY, bird_name TEXT, sighting_date DATE,
    location GEOGRAPHY(POINT, 4326), count INTEGER
);
INSERT INTO bird_sightings (bird_name, sighting_date, location, count) VALUES
('Common Raven', '2024-03-15', ST_GeogFromText('POINT(-0.1276 51.5074)'), 3),
('Bald Eagle', '2024-04-02', ST_GeogFromText('POINT(-122.3321 47.6062)'), 1);
