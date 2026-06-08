let _paymentEnabled = false;
let _priceDisplay = '';

document.addEventListener('DOMContentLoaded', async () => {
    populateSelects();
    setupValidationMessages();
    setupAutocomplete();
    await loadPaymentConfig();
    setupFormSubmit();
    setupGenerateAnother();
});

async function loadPaymentConfig() {
    try {
        const resp = await fetch('/api/payment-config');
        const cfg = await resp.json();
        _paymentEnabled = cfg.enabled;
        if (_paymentEnabled) {
            const rupees = (cfg.amount / 100).toFixed(0);
            _priceDisplay = `₹${rupees}`;
            const btnText = document.querySelector('#submitBtn .btn-text');
            btnText.textContent = `Pay ${_priceDisplay} & Generate Kundli`;
        }
    } catch (err) {
        console.warn('Could not load payment config, falling back to free mode');
    }
}

function populateSelects() {
    const daySelect = document.getElementById('day');
    daySelect.innerHTML = '<option value="">Day</option>';
    for (let i = 1; i <= 31; i++) {
        daySelect.innerHTML += `<option value="${i}">${i}</option>`;
    }

    const hourSelect = document.getElementById('hour');
    hourSelect.innerHTML = '<option value="">Hour</option>';
    for (let i = 0; i <= 23; i++) {
        const h12 = i % 12 || 12;
        const suffix = i < 12 ? 'AM' : 'PM';
        hourSelect.innerHTML += `<option value="${i}">${h12} ${suffix}</option>`;
    }

    const minSelect = document.getElementById('min');
    minSelect.innerHTML = '<option value="">Min</option>';
    for (let i = 0; i <= 59; i++) {
        minSelect.innerHTML += `<option value="${i}">${i.toString().padStart(2, '0')}</option>`;
    }
}

// --- Field-specific validation messages ---

const FIELD_MESSAGES = {
    name: 'Please enter your full name.',
    phone: 'Please enter your contact number.',
    day: 'Please select your birth day.',
    month: 'Please select your birth month.',
    year: 'Please enter your birth year.',
    hour: 'Please select your birth hour.',
    min: 'Please select your birth minute.',
    place: 'Please enter your birth place.',
};

function setupValidationMessages() {
    Object.keys(FIELD_MESSAGES).forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('invalid', () => {
            if (el.validity.valueMissing) {
                el.setCustomValidity(FIELD_MESSAGES[id]);
            } else if (id === 'year' && (el.validity.rangeUnderflow || el.validity.rangeOverflow)) {
                el.setCustomValidity('Please enter a year between 1900 and 2100.');
            } else if (id === 'phone' && el.validity.typeMismatch) {
                el.setCustomValidity('Please enter a valid 10-digit mobile number.');
            } else {
                el.setCustomValidity(''); // fall back to native message for other cases
            }
        });
        // Clear the custom error as soon as the user edits the field
        const clear = () => el.setCustomValidity('');
        el.addEventListener('input', clear);
        el.addEventListener('change', clear);
    });
}

// --- Place Autocomplete ---

let debounceTimer = null;

function setupAutocomplete() {
    const input = document.getElementById('place');
    const dropdown = document.getElementById('placeDropdown');

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const query = input.value.trim();
        if (query.length < 3) {
            dropdown.classList.remove('active');
            return;
        }
        debounceTimer = setTimeout(() => searchPlace(query), 300);
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) {
            dropdown.classList.remove('active');
        }
    });
}

async function searchPlace(query) {
    const dropdown = document.getElementById('placeDropdown');
    try {
        const resp = await fetch(`/api/geo-search?place=${encodeURIComponent(query)}`);
        const data = await resp.json();
        const places = data.geonames || [];

        if (places.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-item"><span class="place-detail">No results found</span></div>';
            dropdown.classList.add('active');
            return;
        }

        dropdown.innerHTML = places.map(p => `
            <div class="autocomplete-item"
                 data-lat="${p.latitude}"
                 data-lon="${p.longitude}"
                 data-tz="${p.timezone_id}"
                 data-name="${p.place_name}, ${p.country_code}">
                <div class="place-name">${p.place_name}</div>
                <div class="place-detail">${p.country_code} &bull; ${p.latitude}, ${p.longitude}</div>
            </div>
        `).join('');

        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => selectPlace(item));
        });

        dropdown.classList.add('active');
    } catch (err) {
        console.error('Place search failed:', err);
    }
}

function selectPlace(item) {
    const name = item.dataset.name;
    const lat = parseFloat(item.dataset.lat);
    const lon = parseFloat(item.dataset.lon);
    const tzId = item.dataset.tz;

    document.getElementById('place').value = name;
    document.getElementById('lat').value = lat;
    document.getElementById('lon').value = lon;
    document.getElementById('placeDropdown').classList.remove('active');

    const infoDiv = document.getElementById('placeInfo');
    const infoText = document.getElementById('placeInfoText');
    infoText.textContent = `Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}, Timezone: ${tzId}`;
    infoDiv.style.display = 'block';

    resolveTimezone(lat, lon, tzId);
}

async function resolveTimezone(lat, lon, tzId) {
    const day = document.getElementById('day').value || 1;
    const month = document.getElementById('month').value || 1;
    const year = document.getElementById('year').value || 2000;
    const hour = document.getElementById('hour').value || 12;
    const min = document.getElementById('min').value || 0;

    try {
        const params = new URLSearchParams({
            day, month, year, hour, min,
            lat: lat.toString(),
            lon: lon.toString(),
            tzone: '5.5',
        });
        const resp = await fetch(`/api/timezone?${params}`);
        const data = await resp.json();
        if (data.timezone !== undefined) {
            document.getElementById('tzone').value = data.timezone;
            const infoText = document.getElementById('placeInfoText');
            infoText.textContent = `Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}, Timezone: ${data.timezone}`;
        }
    } catch (err) {
        const tzMap = {
            'Asia/Kolkata': 5.5, 'Asia/Colombo': 5.5,
            'Asia/Kathmandu': 5.75, 'Asia/Dhaka': 6,
            'Asia/Karachi': 5, 'Asia/Dubai': 4,
            'Europe/London': 0, 'America/New_York': -5,
            'America/Chicago': -6, 'America/Los_Angeles': -8,
        };
        const tz = tzMap[tzId];
        if (tz !== undefined) {
            document.getElementById('tzone').value = tz;
        }
    }
}

// --- Form Submission ---

function validatePhone(raw) {
    // Strip spaces, dashes, parentheses, and a leading +91 / 91 / 0
    const digits = raw.replace(/[\s\-()]/g, '').replace(/^(\+?91|0)/, '');
    return /^[6-9]\d{9}$/.test(digits) ? digits : null;
}

function setupFormSubmit() {
    const form = document.getElementById('kundliForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const lat = document.getElementById('lat').value;
        const lon = document.getElementById('lon').value;
        if (!lat || !lon) {
            showError('Please select a place from the autocomplete dropdown.');
            return;
        }

        const phone = validatePhone(document.getElementById('phone').value.trim());
        if (!phone) {
            showError('Please enter a valid 10-digit mobile number.');
            return;
        }

        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoader = submitBtn.querySelector('.btn-loader');
        submitBtn.disabled = true;
        btnText.textContent = 'Processing...';
        btnLoader.style.display = 'inline-block';
        hideError();

        const payload = {
            name: document.getElementById('name').value.trim(),
            phone: phone,
            day: parseInt(document.getElementById('day').value),
            month: parseInt(document.getElementById('month').value),
            year: parseInt(document.getElementById('year').value),
            hour: parseInt(document.getElementById('hour').value),
            min: parseInt(document.getElementById('min').value),
            lat: parseFloat(lat),
            lon: parseFloat(lon),
            tzone: parseFloat(document.getElementById('tzone').value),
            lang: document.getElementById('lang').value,
            place: document.getElementById('place').value,
        };

        if (_paymentEnabled) {
            await handlePaidFlow(payload);
        } else {
            await handleFreeFlow(payload);
        }
    });
}

async function handleFreeFlow(payload) {
    try {
        const resp = await fetch('/generate-kundli', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${resp.status}`);
        }

        const blob = await resp.blob();
        showPdfResult(blob, payload.name, payload.year);
    } catch (err) {
        showError(err.message || 'Failed to generate Kundli. Please try again.');
    } finally {
        resetSubmitButton();
    }
}

async function handlePaidFlow(payload) {
    try {
        const orderResp = await fetch('/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!orderResp.ok) {
            const err = await orderResp.json().catch(() => ({}));
            throw new Error(err.detail || 'Could not start payment');
        }
        const order = await orderResp.json();

        const options = {
            key: order.key_id,
            amount: order.amount,
            currency: order.currency,
            name: 'Bloomx Kundli',
            description: 'Personalized Kundli Report',
            order_id: order.order_id,
            prefill: { name: order.name },
            theme: { color: '#b8860b' },
            handler: async function (response) {
                await verifyAndGenerate(response, payload.name, payload.year);
            },
            modal: {
                ondismiss: function () {
                    resetSubmitButton();
                },
            },
        };
        const rzp = new Razorpay(options);
        rzp.on('payment.failed', function (resp) {
            showError('Payment failed: ' + (resp.error?.description || 'unknown error'));
            resetSubmitButton();
        });
        rzp.open();
    } catch (err) {
        showError(err.message || 'Something went wrong. Please try again.');
        resetSubmitButton();
    }
}

async function verifyAndGenerate(rzpResponse, name, year) {
    const btnText = document.querySelector('#submitBtn .btn-text');
    btnText.textContent = 'Confirming payment...';
    try {
        const resp = await fetch('/verify-and-generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                razorpay_order_id: rzpResponse.razorpay_order_id,
                razorpay_payment_id: rzpResponse.razorpay_payment_id,
                razorpay_signature: rzpResponse.razorpay_signature,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server error: ${resp.status}`);
        }
        const result = await resp.json();
        showThankYouPage(name, result.order_id, result.payment_id);
    } catch (err) {
        showError(
            (err.message || 'Something went wrong') +
            ' — please save your payment ID and contact us. Your payment is secure.'
        );
    } finally {
        resetSubmitButton();
    }
}

function showPdfResult(blob, name, year) {
    const url = URL.createObjectURL(blob);
    document.getElementById('pdfFrame').src = url;
    const dl = document.getElementById('pdfDownload');
    dl.href = url;
    dl.download = `kundli_${name.replace(/[^a-zA-Z0-9 _-]/g, '')}_${year}.pdf`;
    document.getElementById('pdfResult').style.display = 'block';
    document.getElementById('pdfResult').scrollIntoView({ behavior: 'smooth' });
}

function resetSubmitButton() {
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = false;
    const label = _paymentEnabled ? `Pay ${_priceDisplay} & Generate Kundli` : 'Generate Kundli PDF';
    submitBtn.querySelector('.btn-text').textContent = label;
    submitBtn.querySelector('.btn-loader').style.display = 'none';
}

function setupGenerateAnother() {
    document.getElementById('generateAnother').addEventListener('click', () => {
        document.getElementById('pdfResult').style.display = 'none';
        const frame = document.getElementById('pdfFrame');
        if (frame.src.startsWith('blob:')) {
            URL.revokeObjectURL(frame.src);
        }
        frame.src = '';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

function showThankYouPage(name, orderId, paymentId) {
    const form = document.getElementById('kundliForm');
    if (form) form.style.display = 'none';

    const pdfPanel = document.getElementById('pdfResult');
    if (pdfPanel) pdfPanel.style.display = 'none';

    let panel = document.getElementById('thankYouPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'thankYouPanel';
        panel.style.cssText = `
            max-width: 600px;
            margin: 40px auto;
            padding: 40px;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            text-align: center;
            font-family: sans-serif;
        `;
        document.querySelector('main, body').appendChild(panel);
    }

    panel.innerHTML = `
        <div style="font-size: 64px; margin-bottom: 16px;">\u{1F64F}</div>
        <h2 style="color: #b8860b; margin-bottom: 16px;">धन्यवाद, ${escapeHtml(name)}!</h2>
        <p style="font-size: 18px; line-height: 1.6; color: #333; margin-bottom: 12px;">
            <strong>आपकी कुंडली तैयार हो रही है।</strong>
        </p>
        <p style="font-size: 15px; line-height: 1.6; color: #555; margin-bottom: 24px;">
            हम जल्द ही आपकी कुंडली आप तक पहुँचा देंगे।<br>
            <span style="font-size: 13px; color: #888;">
            We will deliver your Kundli to you shortly.
            </span>
        </p>
        <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 16px;
                    border-radius: 8px; margin-bottom: 24px; color: #155724;">
            <strong>✓ Payment confirmed</strong>
        </div>
        <div style="background: #f7f3e8; padding: 16px; border-radius: 8px;
                    font-size: 14px; color: #5a4a2a; margin-bottom: 24px;">
            <strong>Order ID:</strong> ${escapeHtml(orderId)}<br>
            <strong>Payment ID:</strong> ${escapeHtml(paymentId)}<br>
            <em style="font-size: 12px;">Please save these for reference</em>
        </div>
        <p style="font-size: 14px; color: #888;">
            कोई समस्या हो तो संपर्क करें:
            <a href="https://wa.me/918839523452" style="color: #25D366; font-weight: 500;">
                +91-8839523452 (WhatsApp)
            </a>
        </p>
        <p style="font-size: 12px; color: #aaa; margin-top: 16px;">
            आप यह पेज बंद कर सकते हैं — आपकी कुंडली तैयार होती रहेगी।<br>
            <em>You can close this page — your Kundli is being prepared in the background.</em>
        </p>
    `;

    panel.scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function showError(msg) {
    const el = document.getElementById('errorMsg');
    el.textContent = msg;
    el.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMsg').style.display = 'none';
}
