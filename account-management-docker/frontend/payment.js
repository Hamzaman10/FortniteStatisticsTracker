console.log("payment.js loaded");

const base = window.APP_CONFIG.PAYMENT_URL;

// Get token from storage
function getIdToken() {
    return localStorage.getItem("id_token");
}

// Decode user ID from token
function getUserId() {
    const token = getIdToken();
    if (!token) return null;

    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.sub;
    } catch (e) {
        console.error("Token decode error", e);
        return null;
    }
}

const userId = getUserId();
console.log("USER ID:", userId);

async function loadSavedCards() {
    const container = document.getElementById("savedCards");
    container.innerHTML = '<p style="color:#888;">Loading cards...</p>'; // Show loading state

    try {
        const res = await fetch(`${base}/cards?user_id=${userId}`);
        
        // If the backend isn't reachable yet, stop here without a scary error
        if (!res.ok) {
            throw new Error(`Server returned ${res.status}`);
        }

        const cards = await res.json();

        container.innerHTML = ""; // Clear loading message

        if (cards.length === 0) {
            container.innerHTML = '<p style="color:#aaa; font-style:italic;">No saved payment methods.</p>';
            return;
        }

        cards.forEach(c => {
            container.innerHTML += `
                <div class="saved-card-item">
                    <div class="card-info">
                        <span class="card-brand">VISA ending in ${c.last4}</span>
                        Expires ${c.exp_month}/${c.exp_year}
                    </div>
                    <button class="btn btn-delete" onclick="deleteCard('${c.card_token}')">Remove</button>
                </div>
            `;
        });

    } catch (err) {
        console.warn("Could not load cards (likely network/CORS issue):", err);
        // Don't show a scary red error for network blocks in Cloud9
        container.innerHTML = '<p style="color:#aaa;">No cards found (or connection pending).</p>';
    }
}

async function saveCard() {
    const statusDiv = document.getElementById("paymentStatus");
    statusDiv.textContent = "Processing...";
    statusDiv.style.color = "#4db8ff";

    const payload = {
        name_on_card: document.getElementById("name_on_card").value,
        card_number: document.getElementById("card_number").value,
        exp_month: parseInt(document.getElementById("exp_month").value),
        exp_year: parseInt(document.getElementById("exp_year").value),
        billing_zip: document.getElementById("billing_zip").value,
        billing_country: document.getElementById("billing_country").value
    };

    try {
        const res = await fetch(`${base}/card?user_id=${userId}`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (!res.ok) {
            // SHOW THE ERROR FROM THE BACKEND (e.g. "Limit reached")
            throw new Error(data.detail || "Failed to save");
        }

        statusDiv.textContent = "Payment method saved!";
        statusDiv.style.color = "#4db8ff";
        loadSavedCards(); // Refresh the list

    } catch (err) {
        console.error("Save FAILED:", err);
        statusDiv.textContent = err.message; // Display "You can only add 1 payment method..."
        statusDiv.style.color = "#ff4d4d";   // Make it red
    }
}

async function deleteCard(token) {
    try {
        await fetch(`${base}/card?user_id=${userId}&card_token=${token}`, { method: "DELETE" });
        loadSavedCards();
    } catch (err) {
        console.error("Delete FAILED:", err);
    }
}

document.getElementById("saveCardBtn").onclick = saveCard;

loadSavedCards();
