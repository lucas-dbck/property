const DEFAULT_APP_URL = "https://propertyreal.vercel.app"

const appUrlInput = document.getElementById("appUrl")
const importButton = document.getElementById("importButton")
const statusText = document.getElementById("status")

init()

async function init() {
  const stored = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL })
  appUrlInput.value = stored.appUrl
  appUrlInput.addEventListener("change", saveAppUrl)
  importButton.addEventListener("click", importCurrentListing)
}

async function saveAppUrl() {
  await chrome.storage.sync.set({ appUrl: cleanAppUrl(appUrlInput.value) })
}

async function importCurrentListing() {
  setStatus("Reading listing...", "ok")
  importButton.disabled = true

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab?.id || !tab.url?.includes("immoweb.be")) {
      throw new Error("Open an Immoweb listing tab first.")
    }

    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["scraper.js"],
    })

    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.__yieldDeskScrapeImmowebListing(),
    })

    if (!result?.values || Object.keys(result.values).length === 0) {
      throw new Error("No listing data found on this page.")
    }

    const appUrl = cleanAppUrl(appUrlInput.value || DEFAULT_APP_URL)
    await chrome.storage.sync.set({ appUrl })
    const encoded = encodePayload(result)
    await chrome.tabs.create({ url: `${appUrl}/analyze?import=${encoded}` })
    setStatus("Sent to YieldDesk.", "ok")
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not import this listing.", "error")
  } finally {
    importButton.disabled = false
  }
}

function cleanAppUrl(value) {
  return String(value || DEFAULT_APP_URL).trim().replace(/\/+$/, "")
}

function encodePayload(payload) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
}

function setStatus(message, tone) {
  statusText.textContent = message
  statusText.className = tone
}
