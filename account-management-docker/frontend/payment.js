console.log("payment.js loaded");

const STORAGE_KEY = "saved_payment_card";

document.addEventListener("DOMContentLoaded", () => {
    const savedCardsDiv = document.getElementById("savedCards");
    const saveBtn = document.getElementById("saveCardBtn");
    const statusDiv = document.getElementById("paymentStatus");

    // Load UI
    function loadCard() {
        const raw = localStorage.getItem(STORAGE_KEY);

        if (!raw) {
            savedCardsDiv.innerHTML = `<p style="color:#aaa; font-style:italic;">No saved payment methods.</p>`;
            return;
        }

        const card = JSON.parse(raw);

        savedCardsDiv.innerHTML = `
            <div class="saved-card-item">
                <div class="card-info">
                    <span class="card-brand">VISA ending in ${card.last4}</span>
                    Expires ${card.exp_month}/${card.exp_year}
                </div>
                <button class="btn btn-delete" id="deleteCardBtn">Remove</button>
            </div>
        `;

        // DELETE BUTTON LOGIC (works perfectly)
        document.getElementById("deleteCardBtn").onclick = () => {
            localStorage.removeItem(STORAGE_KEY);
            loadCard(); // refresh UI
        };
    }

    // Save card button
    saveBtn.onclick = () => {
        const name = document.getElementById("name_on_card").value;
        const number = document.getElementById("card_number").value;
        const expMonth = document.getElementById("exp_month").value;
        const expYear = document.getElementById("exp_year").value;
        const zip = document.getElementById("billing_zip").value;
        const country = document.getElementById("billing_country").value;

        // Validation
        if (!name || !number || !expMonth || !expYear || !zip || !country) {
            statusDiv.textContent = "Missing fields.";
            statusDiv.style.color = "#ff4d4d";
            return;
        }

        const last4 = number.slice(-4);

        const card = {
            last4,
            exp_month: expMonth,
            exp_year: expYear,
            name_on_card: name,
            billing_zip: zip,
            billing_country: country,
            created_at: new Date().toISOString()
        };

        localStorage.setItem(STORAGE_KEY, JSON.stringify(card));

        statusDiv.textContent = "Payment method saved!";
        statusDiv.style.color = "#4db8ff";

        loadCard();
    };

    // Initial load
    loadCard();
});

