const fs = require("node:fs")
const vm = require("node:vm")

const source = fs.readFileSync(`${__dirname}/scraper.js`, "utf8")
const sandbox = { window: {}, document: {}, HTMLMetaElement: class HTMLMetaElement {} }
vm.createContext(sandbox)
vm.runInContext(source, sandbox)

const price = vm.runInContext('extractPrice("House for sale €579.000 579 views")', sandbox)
const rent = vm.runInContext('estimateMonthlyRent({ city: "Duffel", postcode: "2570", area_sqm: 119, energy_score: "B" })', sandbox)

if (price !== 579000) {
  throw new Error(`Expected price 579000, got ${price}`)
}

if (rent !== 1716) {
  throw new Error(`Expected rent 1716, got ${rent}`)
}

console.log("Extension parser checks passed")
