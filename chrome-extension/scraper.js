window.__yieldDeskScrapeImmowebListing = function scrapeImmowebListing() {
  const text = document.body?.innerText || ""
  const compact = text.replace(/\s+/g, " ").trim()
  const url = window.location.href
  const fromUrl = parseImmowebUrl(url)
  const jsonData = readJsonData()

  const values = compactObject({
    source_url: url,
    purchase_price: firstUseful([
      readJsonNumber(jsonData, ["price", "mainValue"]),
      readJsonNumber(jsonData, ["price", "value"]),
      readJsonNumber(jsonData, ["offers", "price"]),
      extractPrice(compact),
    ]),
    city: firstUseful([
      readJsonString(jsonData, ["address", "locality"]),
      readJsonString(jsonData, ["address", "addressLocality"]),
      fromUrl.city,
    ]),
    postcode: firstUseful([
      readJsonString(jsonData, ["address", "postalCode"]),
      fromUrl.postcode,
    ]),
    area_sqm: firstUseful([
      readJsonNumber(jsonData, ["property", "netHabitableSurface"]),
      readJsonNumber(jsonData, ["property", "habitableSurface"]),
      findNumber(compact, [
        /(?:Living area|Habitable surface|Surface habitable|Woonoppervlakte|Bewoonbare oppervlakte|Surface|Oppervlakte)\s*([0-9]{2,4})\s*(?:m2|m²|sqm)/i,
        /\b([0-9]{2,4})\s*(?:m2|m²|sqm)\b/i,
      ]),
    ]),
    bedrooms: firstUseful([
      readJsonNumber(jsonData, ["property", "bedroomCount"]),
      findNumber(compact, [
        /(?:Bedrooms?|Slaapkamers?|Chambres?)\s*[:\-]?\s*([0-9]+)/i,
        /\b([0-9]+)\s*(?:bedrooms?|slaapkamers?|chambres?)\b/i,
      ]),
    ]),
    bathrooms: firstUseful([
      readJsonNumber(jsonData, ["property", "bathroomCount"]),
      findNumber(compact, [
        /(?:Bathrooms?|Badkamers?|Salles? de bains?)\s*[:\-]?\s*([0-9]+)/i,
        /\b([0-9]+)\s*(?:bathrooms?|badkamers?|salles? de bains?)\b/i,
      ]),
    ]),
    energy_score: firstUseful([
      readJsonString(jsonData, ["energy", "epcScore"]),
      readJsonString(jsonData, ["energy", "class"]),
      findText(compact, [
        /\b(?:EPC|PEB|Energy score|Energiescore)\b[^A-G+]{0,80}\b(A\+|A|B|C|D|E|F|G)\b/i,
      ])?.toUpperCase(),
    ]),
    property_type: fromUrl.propertyType,
  })

  if (values.purchase_price) values.price = values.purchase_price
  const estimatedRent = estimateMonthlyRent(values)
  if (estimatedRent) {
    values.monthly_rent = estimatedRent
    values.estimated_rent = estimatedRent
  }

  const foundLabels = [
    ["purchase_price", "Price"],
    ["city", "City"],
    ["area_sqm", "Living area"],
    ["bedrooms", "Bedrooms"],
    ["energy_score", "Energy score"],
  ]
  const found = foundLabels.filter(([key]) => values[key]).map(([, label]) => label)
  const missing = foundLabels.filter(([key]) => !values[key]).map(([, label]) => label)
  const imageMeta = document.querySelector('meta[property="og:image"]')

  return {
    values,
    feedback: {
      found,
      missing,
      status: missing.length ? "partial" : "success",
      method: "chrome_extension",
      message: missing.length
        ? "Imported visible page data from Chrome. Review missing fields."
        : "Imported visible page data from Chrome.",
    },
    meta: {
      title: document.querySelector("h1")?.textContent?.trim() || document.title,
      address: [values.city, values.postcode].filter(Boolean).join(", "),
      listingUrl: url,
      imageUrl: imageMeta instanceof HTMLMetaElement ? imageMeta.content : undefined,
    },
  }
}

function parseImmowebUrl(url) {
  const parts = new URL(url).pathname.split("/").filter(Boolean).map(decodeURIComponent)
  const lowered = parts.map((part) => part.toLowerCase())
  const propertyTypes = ["apartment", "house", "studio", "villa", "duplex", "penthouse", "land"]
  const propertyType = propertyTypes.find((type) => lowered.includes(type))
  const postcodeIndex = parts.findIndex((part) => /^[1-9][0-9]{3}$/.test(part))
  const postcode = postcodeIndex >= 0 ? parts[postcodeIndex] : undefined
  const city = postcodeIndex > 0 ? titleCase(parts[postcodeIndex - 1].replace(/-/g, " ")) : undefined
  return { city, postcode, propertyType }
}

function readJsonData() {
  const objects = []
  document.querySelectorAll('script[type="application/ld+json"], script[type="application/json"], script#__NEXT_DATA__').forEach((script) => {
    try {
      objects.push(JSON.parse(script.textContent || "{}"))
    } catch {
      // Ignore scripts that are not pure JSON.
    }
  })
  return objects
}

function readJsonNumber(objects, path) {
  for (const object of objects) {
    const found = deepFindPath(object, path)
    const number = toNumber(found)
    if (number) return number
  }
  return undefined
}

function readJsonString(objects, path) {
  for (const object of objects) {
    const found = deepFindPath(object, path)
    if (typeof found === "string" && found.trim()) return found.trim()
    if (typeof found === "number") return String(found)
  }
  return undefined
}

function deepFindPath(value, path) {
  if (!value || typeof value !== "object") return undefined
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = deepFindPath(item, path)
      if (found !== undefined) return found
    }
    return undefined
  }

  let current = value
  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in current)) {
      current = undefined
      break
    }
    current = current[key]
  }
  if (current !== undefined && current !== null && current !== "") return current

  for (const child of Object.values(value)) {
    const found = deepFindPath(child, path)
    if (found !== undefined) return found
  }
  return undefined
}

function extractPrice(text) {
  const labeled = findNumber(text, [
    /(?:Price|Asking price|Sale price|Prijs|Vraagprijs|Prix|Prix demand(?:e|é))\s*(?:€|EUR)?\s*([0-9]{1,3}(?:[.,\u00a0][0-9]{3})+|[0-9]{5,8})(?![0-9.,])/i,
    /(?:€|EUR)\s*([0-9]{1,3}(?:[.,\u00a0][0-9]{3})+|[0-9]{5,8})(?![0-9.,])\s*(?:asking|sale|price|prijs|prix)/i,
  ])
  if (labeled) return labeled

  const candidates = [...text.matchAll(/(?:€|EUR)\s*([0-9]{1,3}(?:[.,\u00a0][0-9]{3})+|[0-9]{5,8})(?![0-9.,])/gi)]
    .map((match) => toNumber(match[1]))
    .filter((value) => value && value >= 50000 && value <= 5000000)
  return candidates[0]
}

function findNumber(text, patterns) {
  for (const pattern of patterns) {
    const match = text.match(pattern)
    const number = toNumber(match?.[1])
    if (number !== undefined) return number
  }
  return undefined
}

function findText(text, patterns) {
  for (const pattern of patterns) {
    const match = text.match(pattern)
    if (match?.[1]) return match[1].trim()
  }
  return undefined
}

function toNumber(value) {
  if (value === undefined || value === null || value === "") return undefined
  const raw = String(value).trim()
  const priceLike = raw.match(/[0-9]{1,3}(?:[.,\u00a0][0-9]{3})+|[0-9]{5,8}/)
  const cleaned = (priceLike ? priceLike[0] : raw).replace(/[^0-9.,]/g, "")
  if (!cleaned) return undefined
  const decimalComma = cleaned.includes(",") && !cleaned.includes(".") && cleaned.split(",").pop().length !== 3
  const normalized = decimalComma
    ? cleaned.replace(/\./g, "").replace(",", ".")
    : cleaned.replace(/[.,](?=\d{3}\b)/g, "")
  const number = Number.parseFloat(normalized)
  return Number.isFinite(number) ? number : undefined
}

function estimateMonthlyRent(values) {
  const area = Number(values.area_sqm || 0)
  const bedrooms = Number(values.bedrooms || 0)
  const rate = rentRateForLocation(values.city, values.postcode)
  let rent = area > 0 ? area * rate : bedrooms > 0 ? 650 + bedrooms * 275 : 0
  const energy = String(values.energy_score || "").trim().toLowerCase()
  const energyMultipliers = { "a+": 1.06, a: 1.05, b: 1.03, c: 1, d: 0.97, e: 0.94, f: 0.9, g: 0.86 }
  rent *= energyMultipliers[energy] || 1
  return rent > 0 ? Math.round(rent) : undefined
}

function rentRateForLocation(city, postcode) {
  const cityRates = {
    brussels: 18,
    bruxelles: 18,
    etterbeek: 19,
    ixelles: 20,
    elsene: 20,
    uccle: 19,
    ukkel: 19,
    schaerbeek: 17,
    antwerp: 16,
    antwerpen: 16,
    ghent: 17,
    gent: 17,
    leuven: 19,
    mechelen: 15.5,
    duffel: 14,
    zemst: 14.5,
    malderen: 13.5,
    londerzeel: 13.5,
    vilvoorde: 15,
    grimbergen: 15,
    zaventem: 16,
    charleroi: 10.5,
    liege: 12,
    luik: 12,
  }
  const key = normalizeLocation(city)
  if (cityRates[key]) return cityRates[key]
  const code = Number.parseInt(String(postcode || ""), 10)
  if (code >= 1000 && code <= 1299) return 18
  if (code >= 2000 && code <= 2999) return 15
  if (code >= 3000 && code <= 3499) return 16.5
  if (code >= 1500 && code <= 1999) return 15
  if (code >= 9000 && code <= 9999) return 14.5
  if (code >= 8000 && code <= 8999) return 14
  if (code >= 3500 && code <= 3999) return 13
  if (code >= 4000 && code <= 7999) return 11.5
  return 14
}

function normalizeLocation(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
}

function firstUseful(values) {
  return values.find((value) => value !== undefined && value !== null && value !== "")
}

function compactObject(input) {
  return Object.fromEntries(Object.entries(input).filter(([, value]) => value !== undefined && value !== null && value !== ""))
}

function titleCase(value) {
  return String(value || "").replace(/\w\S*/g, (part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
}
