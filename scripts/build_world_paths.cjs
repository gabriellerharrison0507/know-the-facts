#!/usr/bin/env node
/* Builds assets/map/world-paths.json: one SVG path per country, keyed by
   ISO 3166-1 alpha-3 code, in an Equal Earth projection (equal-area, so a
   country's share of the map matches its share of the land).

   Geometry: world-atlas 2.x countries-110m (Natural Earth 1:110m, public
   domain; packaging ISC). Numeric -> alpha-3 codes: i18n-iso-countries.
   At 1:110m some small states (e.g. Singapore, Malta, most island states)
   have no shape; the page's country table still lists them.

   Run: npm i d3-geo topojson-client world-atlas@2 i18n-iso-countries
        NODE_PATH=<that node_modules> node scripts/build_world_paths.cjs */
const fs = require("fs");
const path = require("path");
const { geoEqualEarth, geoPath } = require("d3-geo");
const { feature } = require("topojson-client");
const topo = require("world-atlas/countries-110m.json");
const codes = require("i18n-iso-countries/codes.json");

const W = 960, H = 468;
const num2a3 = Object.fromEntries(codes.map(c => [c[2], c[1]]));
// Shapes without an ISO numeric id in Natural Earth
const byName = { Kosovo: "XKX", "N. Cyprus": null, Somaliland: null };

const fc = feature(topo, topo.objects.countries);
fc.features = fc.features.filter(f => f.properties.name !== "Antarctica");
const proj = geoEqualEarth().fitExtent([[2, 2], [W - 2, H - 2]], { type: "Sphere" });
const gp = geoPath(proj).digits(1);

const countries = {};
const unmatched = [];
for (const f of fc.features) {
  let a3 = f.id != null ? num2a3[f.id] : undefined;
  if (a3 === undefined && f.properties.name in byName) a3 = byName[f.properties.name];
  const d = gp(f);
  if (!d) continue;
  if (!a3) { unmatched.push(f.properties.name); a3 = null; }
  if (a3) countries[a3] = countries[a3] ? countries[a3] + d : d;
  else countries["_" + f.properties.name] = d;
}
const out = { viewBox: `0 0 ${W} ${H}`, sphere: geoPath(proj).digits(1)({ type: "Sphere" }), countries };
const dest = path.join(__dirname, "..", "assets/map/world-paths.json");
fs.writeFileSync(dest, JSON.stringify(out));
console.log(`Wrote ${dest}: ${Object.keys(countries).length} shapes, ${fs.statSync(dest).size} bytes; no ISO code: ${unmatched.join(", ")}`);
