const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) ? window.APP_CONFIG.API_BASE.replace(/\/+$/, "") : "";
const WISHLIST_KEY = "wishlist_items";

const loginBtn     = document.getElementById("loginBtn");
const logoutBtn    = document.getElementById("logoutBtn");
const paymentBtn   = document.getElementById("paymentBtn");
const wishlistBtn  = document.getElementById("wishlistBtn");
const statsSection = document.getElementById("statsSection");
const statsBtn     = document.getElementById("statsBtn");
const statsInput   = document.getElementById("statsInput");
const statsResult  = document.getElementById("statsResult");
const shopGrid     = document.getElementById("shopGrid");

let idToken = null;
let userSub = null;
let hasPayment = false;

function extractToken() {
  const hash = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
  const params = new URLSearchParams(hash);
  const t = params.get("id_token");

  if (t) {
    localStorage.setItem("id_token", t);
    window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    return t;
  }
  return localStorage.getItem("id_token");
}

function decodeJwtPayload(token) {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;

    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    const json = atob(b64 + pad);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function getWishlist() {
  try {
    return JSON.parse(localStorage.getItem(WISHLIST_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveWishlist(list) {
  localStorage.setItem(WISHLIST_KEY, JSON.stringify(list));
}

function toggleWishlist(key) {
  const list = getWishlist();
  const next = list.includes(key) ? list.filter(x => x !== key) : [...list, key];
  saveWishlist(next);
  renderShop(window.__shopItems || []);
}

function authHeader() {
  return idToken ? { "Authorization": `Bearer ${idToken}` } : {};
}

async function apiGet(path, params = {}, needsAuth = false) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  });

  const headers = {};
  if (needsAuth) Object.assign(headers, authHeader());

  const res = await fetch(url.toString(), { method: "GET", headers });
  const text = await res.text();

  if (!res.ok) {
    let msg = text;
    try { msg = JSON.parse(text).detail || JSON.parse(text).error || text; } catch {}
    throw new Error(msg || `Request failed (${res.status})`);
  }

  try { return JSON.parse(text); } catch { return text; }
}

function setAuthUI(loggedIn) {
  loginBtn.style.display = loggedIn ? "none" : "inline-block";
  logoutBtn.style.display = loggedIn ? "inline-block" : "none";
  paymentBtn.style.display = loggedIn ? "inline-block" : "none";
  wishlistBtn.style.display = loggedIn ? "inline-block" : "none";
}

function setStatsUIEnabled(enabled) {
  statsSection.style.display = enabled ? "block" : "none";
  if (!enabled) statsResult.innerHTML = "";
}

async function checkPayment() {
  if (!idToken || !userSub) {
    hasPayment = false;
    setStatsUIEnabled(false);
    return;
  }

  try {
    const cards = await apiGet("/cards", { user_id: userSub }, true);
    hasPayment = Array.isArray(cards) && cards.length > 0;
  } catch {
    hasPayment = false;
  }

  setStatsUIEnabled(hasPayment);
}

function renderShop(items) {
  window.__shopItems = items;

  const wishlist = getWishlist();
  const loggedIn = !!idToken;

  if (!Array.isArray(items) || items.length === 0) {
    shopGrid.innerHTML = `<div class="stats-box">No shop items returned.</div>`;
    return;
  }

  shopGrid.innerHTML = items.map((it) => {
    const name = it.name || "Unknown";
    const price = (it.price !== undefined && it.price !== null) ? `${it.price} V-Bucks` : "N/A";
    const storefront = it.storefront || "";
    const key = it.offer_id || name;

    const wished = wishlist.includes(key);

    return `
      <div class="shop-item">
        <div class="item-name">${escapeHtml(name)}</div>
        <div class="item-price">${escapeHtml(price)}</div>
        ${storefront ? `<div class="item-price">${escapeHtml(storefront)}</div>` : ""}

        ${loggedIn ? `
          <button class="wishlist-btn" data-wish="${escapeAttr(key)}">
            ${wished ? "★ Wishlisted" : "☆ Add to Wishlist"}
          </button>
        ` : `
          <button class="wishlist-btn disabled" disabled>Login to Wishlist</button>
        `}
      </div>
    `;
  }).join("");

  shopGrid.querySelectorAll("[data-wish]").forEach((btn) => {
    btn.addEventListener("click", () => toggleWishlist(btn.getAttribute("data-wish")));
  });
}

function renderStats(username, payload) {
  const stats = payload && payload.stats ? payload.stats : null;
  if (!stats) {
    statsResult.innerHTML = `<div class="stats-box">No stats returned.</div>`;
    return;
  }

  function row(label, value) {
    const v = (value === undefined || value === null) ? "N/A" : String(value);
    return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(v)}</td></tr>`;
  }

  statsResult.innerHTML = `
    <h3 style="text-align:center; margin-bottom:20px; color:#4db8ff; font-size:22px;">
      Stats for ${escapeHtml(username)}
    </h3>

    <table class="stats-table">
      <tr><th>Stat</th><th>Value</th></tr>
      ${row("Wins", stats.wins)}
      ${row("Total Matches", stats.matches)}
      ${row("Kills", stats.kills)}
      ${row("Deaths", stats.deaths)}
      ${row("Damage Done", stats.damage_done)}
      ${row("Damage Taken", stats.damage_taken)}
      ${row("Accuracy", stats.accuracy)}
      ${row("Assists", stats.assists)}
      ${row("Revives", stats.revives)}
      ${row("Hours Played", stats.hours_played)}
      ${row("Matches Per Day", stats.matches_per_day)}
      ${row("Score Per Minute", stats.score_per_minute)}
    </table>
  `;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[c]));
}

function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

loginBtn.onclick = () => {
  const url =
    `${window.APP_CONFIG.DOMAIN}/login?client_id=${window.APP_CONFIG.CLIENT_ID}` +
    `&response_type=token&redirect_uri=${encodeURIComponent(window.APP_CONFIG.REDIRECT)}`;
  window.location.href = url;
};

logoutBtn.onclick = () => {
  localStorage.removeItem("id_token");
  const logoutUrl =
    `${window.APP_CONFIG.DOMAIN}/logout?client_id=${window.APP_CONFIG.CLIENT_ID}` +
    `&logout_uri=${encodeURIComponent(window.APP_CONFIG.REDIRECT)}`;
  window.location.href = logoutUrl;
};

statsBtn.onclick = async () => {
  const username = statsInput.value.trim();
  if (!username) {
    statsResult.innerHTML = "<p>Please enter a username.</p>";
    return;
  }

  if (!hasPayment) {
    statsResult.innerHTML = "<p>You must add a payment method before viewing stats.</p>";
    return;
  }

  try {
    const data = await apiGet("/stats", { username, platform: "epic" }, true);
    renderStats(username, data);
  } catch (e) {
    statsResult.innerHTML = `<p>${escapeHtml(e.message || "Failed to fetch stats")}</p>`;
  }
};

async function init() {
  idToken = extractToken();
  const claims = idToken ? decodeJwtPayload(idToken) : null;
  userSub = claims && claims.sub ? claims.sub : null;

  setAuthUI(!!idToken);

  try {
    const shop = await apiGet("/itemshop");
    const items = shop.items_preview || shop.items || [];
    renderShop(items);
  } catch (e) {
    shopGrid.innerHTML = `<div class="stats-box">${escapeHtml(e.message || "Failed to load item shop")}</div>`;
  }

  await checkPayment();
}

init();
