document.addEventListener('DOMContentLoaded', function() {
    const heading = document.querySelector('.shops-container');
    const title = document.querySelector('#doc');
    if (heading) {
        get_or_create_user();

        const shops = JSON.parse(document.getElementById('shops-data').textContent);
        const shopsList = document.getElementById('shops-list');
        const filterWrapper = document.getElementById('filter-wrapper');
        const cityFilter = document.getElementById('city-filter');

        // Populate unique cities into dropdown filter
        const uniqueCities = [...new Set(shops.map(shop => shop.city))];
        uniqueCities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            cityFilter.appendChild(option);
        });

        // Trigger Geolocation Verification
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const userLat = position.coords.latitude;
                    const userLng = position.coords.longitude;
                    
                    // Filter shops within 15km using Haversine
                    let nearbyShops = shops.filter(shop => {
                        if (!shop.latitude || !shop.longitude) return false;
                        shop.distance = calculate_real_distance(userLat, userLng, shop.latitude, shop.longitude);
                        return shop.distance <= 15;
                    });

                    // Sort nearby matches by proximity
                    nearbyShops.sort((a, b) => a.distance - b.distance);

                    if (nearbyShops.length > 0) {
                        renderShopsList(nearbyShops);
                    } else {
                        // Fallback if permission allowed but nothing within 15km
                        shopsList.innerHTML = `<p style="padding:0 10px; color:var(--text-muted);">No print shops found within 15km of your location. Please select your city below.</p>`;
                        showCityFilter(shops);
                    }
                },
                (error) => {
                    // Fallback if permission explicitly denied or timed out
                    console.warn("Location access denied or unavailable.");
                    shopsList.innerHTML = `<p style="padding:0 10px; color:var(--text-muted);">Location access disabled. Select your city to find print shops.</p>`;
                    showCityFilter(shops);
                },
                { enableHighAccuracy: true, timeout: 6000 }
            );
        } else {
            showCityFilter(shops);
        }

        // Helper setup to reveal dropdown selection UI
        function showCityFilter(allShops) {
        const filterWrapper = document.getElementById('filter-wrapper');
        const dropdown = document.querySelector('.custom-dropdown');
        const triggerBtn = document.getElementById('dropdown-trigger-btn');
        const selectedText = document.getElementById('selected-city-text');
        const customList = document.getElementById('custom-city-list');

        filterWrapper.style.display = 'block';
        renderShopsList(allShops);

        // Populate unique cities into the custom menu
        const uniqueCities = [...new Set(allShops.map(shop => shop.city))];
        uniqueCities.forEach(city => {
            const li = document.createElement('li');
            li.className = 'dropdown-item';
            li.setAttribute('data-value', city);
            li.textContent = city;
            customList.appendChild(li);
        });

        // Toggle menu dropdown open/close
        triggerBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('is-open');
        });

        // Handle Item Selection
        customList.addEventListener('click', function(e) {
            const clickedItem = e.target.closest('.dropdown-item');
            if (!clickedItem) return;

            // Visual selection updates
            customList.querySelectorAll('.dropdown-item').forEach(item => item.classList.remove('selected'));
            clickedItem.classList.add('selected');
            selectedText.textContent = clickedItem.textContent;
            dropdown.classList.remove('is-open');

            // Filter rendering execution
            const selectedCity = clickedItem.getAttribute('data-value');
            if (selectedCity === 'all') {
                renderShopsList(allShops);
            } else {
                const filtered = allShops.filter(shop => shop.city === selectedCity);
                renderShopsList(filtered);
            }
        });

        // Close menu when clicking anywhere else on screen
        document.addEventListener('click', function() {
            dropdown.classList.remove('is-open');
        });
    }

        // Standardized card layout rendering loop engine
        function renderShopsList(targetShops) {
            if (targetShops.length === 0) {
                shopsList.innerHTML = `<p style="padding:20px; text-align:center;">No shops available here.</p>`;
                return;
            }
            
            let finalHTML = "";
            for (let shop of targetShops) {
                let isClosed = !shop.is_open;
                let btn_type = isClosed ? 'disabled' : '';
                let status = isClosed ? 'closed' : 'open';
                let distanceText = shop.distance && shop.distance !== Infinity ? ` • ${shop.distance.toFixed(1)} km away` : '';

                finalHTML += `
                <div class="shops_container">
                    <div class="shop-header">
                        <span class="status-badge status-${status}">${isClosed ? 'Closed' : 'Open Now'}${distanceText}</span>
                        <a href="https://maps.google.com/?q=${shop.latitude},${shop.longitude}" target="_blank">
                            <div class="location_pin"></div>
                        </a>
                    </div>
                    <button type="submit" ${btn_type} name="shop_id" value="${shop.id}" class="shops_submit">
                        <span class="shop-name">${shop.name}</span>
                        <div class="shop-meta">
                            ${shop.location}, ${shop.landmark}<br>
                            ${shop.city}, ${shop.state}
                        </div>
                    </button>
                </div>`;
            }
            shopsList.innerHTML = finalHTML;
        }
    }
    if (title){
        const toggleBtn = document.getElementById('catalogueToggle');
        const contentPanel = document.getElementById('catalogueContent');
        let pdf_pages;
        if (toggleBtn && contentPanel) {
            toggleBtn.addEventListener('click', function() {
                const chevron = this.querySelector('.up-cat-chevron');
                contentPanel.classList.toggle('is-open');
                chevron.classList.toggle('is-rotated');
            });
        }
        title.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const MAX_SIZE_MB = 500;
                const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

                if (file.size > MAX_SIZE_BYTES) {
                    alert(`File is too large! Max limit is 500MB.`);
                    this.value = "";
                    return;
                }

                let shop_id = document.querySelector('#shop_id').value;
                let main_text = document.querySelector('.main-text');
                let sub_text = document.querySelector('.sub-text');
                let file_name = file.name;
                sub_text.style.display = 'none';

                main_text.innerHTML = `Selected: ${file_name}`;
                main_text.style.color = 'green';

                // Helper block to handle UI rendering once page count is known
                function loadShopItemsAndRender(totalPages) {
                    fetch(`/api/item_list/${shop_id}`)
                        .then(response => response.json())
                        .then(result => {
                            let pageTypeContainer = document.querySelector('.page_type');
                            pageTypeContainer.style.display = 'flex';
                            pageTypeContainer.style.flexDirection = "column";
                            
                            let page_types_innerHTML = ``;
                            let keys = Object.keys(result);

                            for (let i = 0; i < keys.length; i++) {
                                let value = keys[i];
                                let checked = i === 0 ? "checked" : ""; 
                                
                                page_types_innerHTML += `
                                    <label class="radio">
                                        <input ${checked} name="page_type" value="${value}" type="radio" />
                                        <span class="name">${value}</span>
                                    </label>`;
                            }

                            pageTypeContainer.innerHTML = `
                                <div class='row-info'>
                                    <span>Page type: </span>   
                                    <div class="radio-inputs"> 
                                        ${page_types_innerHTML} 
                                    </div>
                                </div>`;

                            // Pass the verified page count down safely
                            display_info(file_name, result, keys[0], totalPages);

                            if (keys.length > 1) {
                                pageTypeContainer.addEventListener('change', function(e) {
                                    if (e.target.name === 'page_type') {
                                        display_info(file_name, result, e.target.value, totalPages);
                                    }
                                });
                            }
                        })
                        .catch(err => console.error("API fetch failed:", err));
                }

                // --- Execution Trigger Controller ---
                if (file.type === "application/pdf" && typeof pdfjsLib !== 'undefined') {
                    const reader = new FileReader();
                    reader.onload = function() {
                        const typedarray = new Uint8Array(this.result);
                        pdfjsLib.getDocument(typedarray).promise.then(function(pdf) {
                            pdf_pages = pdf.numPages;
                            
                            // Execute layout only after promise resolves
                            loadShopItemsAndRender(pdf_pages);
                        }).catch(function(err) {
                            console.error("PDF parsing failed:", err);
                            loadShopItemsAndRender(1); // Error fallback
                        });
                    };
                    reader.readAsArrayBuffer(file);
                } else {
                    // Images, text documents, docx fallbacks default cleanly to 1 page
                    loadShopItemsAndRender(1);
                }
            }
        });

        // Show loading overlay on form submission
        document.querySelector('.up-form').addEventListener('submit', function() {
            const loading = document.querySelector('.loading-panel');
            const overlay = document.querySelector('.up-config-panel');
            overlay.style.display = 'none';
            loading.style.display = 'flex';
        });
    }
});


async function get_or_create_user(){
    const uuid = localStorage.getItem('printo_user_id');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    try {
        const response = await fetch('/api/user', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'uuid': uuid || ''
            }
        });
        
        if (response.ok && uuid){
            localStorage.removeItem('printo_user_id');
        }
    } catch (error) {
        console.error('User init failed:', error);
    }
}

function display_info(file_name,result, selected_type, pdf_pages) {
    // 1. Select the container
    let itemInfoContainer = document.querySelector('.item-info');
    itemInfoContainer.style.display='flex';
    itemInfoContainer.style.flexDirection='column';
    itemInfoContainer.innerHTML = ''; 

    // Data containers
    let is_color = [];
    let is_b2b = [];

    // 2. Extract unique values (Your logic)
    result[selected_type].forEach(arr => {
        if (!is_color.includes(arr.is_color)) {
            is_color.push(arr.is_color);
        }
        if (!is_b2b.includes(arr.is_b2b)) {
            is_b2b.push(arr.is_b2b);
        }
    });
    if (pdf_pages === 1){
        is_b2b = [is_b2b[0]]
    }

    // 3. Build Strings (Template Literals are cleaner than createElement)
    
    // --- Color ---
    let color_options = "";
    is_color.forEach((val, index) => {
        let text = val ? "Color" : "Black & White";
        // Checks the first radio element by default if no selection exists
        let checked = index === 0 ? "checked" : ""; 
        color_options += `
            <label class="radio">
                <input ${checked} name="is_color" value="${val}" type="radio" />
                <span class="name">${text}</span>
            </label>`;
    });

    // --- B2B ---
    let b2b_options = "";
    is_b2b.forEach((val, index) => {
        let text = val ? "Back to Back" : "Single Side";
        let checked = index === 0 ? "checked" : "";
        b2b_options += `
            <label class="radio">
                <input ${checked} name="is_b2b" value="${val}" type="radio" />
                <span class="name">${text}</span>
            </label>`;
    });    

    // 4. Inject everything at once using innerHTML
    // This is faster and cleaner than 3 separate appends
    itemInfoContainer.innerHTML = `
        <div class="row-info">
            <span>Print Color:</span>
            <div class="radio-inputs">
                ${color_options}
            </div>
        </div>
        <div class="row-info">
            <span>Print Side:</span><br>
            <div class="radio-inputs">
                ${b2b_options}
            </div>
        </div>
        <div class="row-info page-range-row">
            <span>Pages:</span>
            <div class="cd-range-group">
                <div class="range-field">
                    <span class="range-label">From</span>
                    <input type="number" class="form-control range-input" id="pageStart" name="page_start" placeholder="1" value="1" min="1" max="${pdf_pages}" oninput="validateRange()">
                </div>
                <div class="range-field">
                    <span class="range-label">To</span>
                    <input type="number" class="form-control range-input" id="pageEnd" name="page_end" placeholder="${pdf_pages}" value="${pdf_pages}" min="1" max="${pdf_pages}" oninput="validateRange()">
                </div>
            </div>
        </div>
        <div class="row-info">
            <span>Copies:</span>
            <div class="cd-stepper-pill">
                <button type="button" class="stepper-action" id="back" onclick="adjustCopies(-1)"> - </button>
                <span id="copiesDisplay" class="stepper-value">1</span>
                <button type="button" class="stepper-action" id="front" onclick="adjustCopies(1)"> + </button>
            </div>
            <input type="hidden" name="quantity" id="hiddenQuantity" value="1">
        </div>
        <div class="row-info">
            <button class="wooden-cart-button" id='submit-btn' type='submit'>
                <svg viewBox="0 0 24 24">
                    <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A.996.996 0 0 0 21.42 4H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"></path>
                </svg>
                <span class="button-text">Add to cart</span>
            </button>
        </div>`;
    
    let upload_icon = document.querySelector('.up-dz-icon-wrap');
    upload_icon.style.display = 'none';
    let browze_btn = document.querySelector('.up-dz-btn');
    browze_btn.innerHTML = 'Browse another file.';
    let submit_btn = itemInfoContainer.querySelector('#submit-btn');
    submit_btn.style.marginTop ='20px';
    submit_btn.style.borderRadius='10px';
    if (pdf_pages == 1){
        let page_selection = document.querySelector('.page-range-row');
        if (page_selection) {
            page_selection.style.display = 'none';
        }
    }
};

function adjustCopies(change) {
    const display = document.getElementById('copiesDisplay');
    const hiddenInput = document.getElementById('hiddenQuantity');
    
    let current = parseInt(display.innerText, 10) || 1;
    let updated = current + change;
    
    // Enforce limits (1 to 20 copies)
    if (updated >= 1 && updated <= 20) {
        display.innerText = updated;
        hiddenInput.value = updated;
        hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

function getPreciseLocation(callback) {
    callback('error');
    /*
    const options = {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
    };

    navigator.geolocation.getCurrentPosition(
        (position) => {
            callback([position.coords.latitude, position.coords.longitude]);
        },
        (error) => {
            console.error("Error fetching location:", error.message);
            callback('error');
        },
        options
    ); */
};

function calculate_distance(user_lat, user_long, shop_lat, shop_long){
    let distance = (shop_long-user_long)**2 + (shop_lat-user_lat)**2 ;
    return distance;
};

function calculate_real_distance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c; 
}

// maps link with route https://www.google.com/maps/dir/?api=1&destination=${lat},${long}&travelmode=walking
// maps link of a place https://www.google.com/maps/search/?api=1&query=${lat},${long}