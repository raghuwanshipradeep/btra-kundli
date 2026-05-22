document.addEventListener('DOMContentLoaded', () => {
    populateSelects();
    setupAutocomplete();
    setupFormSubmit();
    setupGenerateAnother();
});

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
        // Fall back to mapping common timezone IDs
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

        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoader = submitBtn.querySelector('.btn-loader');

        submitBtn.disabled = true;
        btnText.textContent = 'Generating...';
        btnLoader.style.display = 'inline-block';
        hideError();

        const payload = {
            name: document.getElementById('name').value.trim(),
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
            const url = URL.createObjectURL(blob);

            document.getElementById('pdfFrame').src = url;
            const downloadLink = document.getElementById('pdfDownload');
            downloadLink.href = url;
            downloadLink.download = `kundli_${payload.name.replace(/[^a-zA-Z0-9 _-]/g, '')}_${payload.year}.pdf`;

            document.getElementById('pdfResult').style.display = 'block';
            document.getElementById('pdfResult').scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            showError(err.message || 'Failed to generate Kundli. Please try again.');
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = 'Generate Kundli PDF';
            btnLoader.style.display = 'none';
        }
    });
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

function showError(msg) {
    const el = document.getElementById('errorMsg');
    el.textContent = msg;
    el.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMsg').style.display = 'none';
}
