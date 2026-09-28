document.addEventListener('DOMContentLoaded', function() {
    const heading = document.querySelector('.shops-container');
    const title = document.querySelector('#doc');
    if (heading) {
        get_or_create_user();
        const shops = JSON.parse(document.getElementById('shops-data').textContent);
        const shopsList = document.getElementById('shops-list');
        const filterWrapper = document.getElementById('filter-wrapper');
        const cityFilter = document.getElementById('city-filter');
        /* NO CITY FILTER
        // Populate unique cities into dropdown filter
        const uniqueCities = [...new Set(shops.map(shop => shop.city))];
        uniqueCities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            cityFilter.appendChild(option);
        });
        */
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

            filterWrapper.style.display = 'none';
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
        let activePdfInstance = null; // Reference pointer to active document
        
        if (toggleBtn && contentPanel) {
            toggleBtn.addEventListener('click', function() {
                const chevron = this.querySelector('.up-cat-chevron');
                contentPanel.classList.toggle('is-open');
                chevron.classList.toggle('is-rotated');
            });
        }
        let file;
        let file_name;
        title.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                file = this.files[0];
                const MAX_SIZE_MB = 1000;
                const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

                if (file.size > MAX_SIZE_BYTES) {
                    alert(`File is too large! Max limit is 1GB.`);
                    this.value = "";
                    return;
                }

                let shop_id = document.querySelector('#shop_id').value;
                let main_text = document.querySelector('.main-text');
                let sub_text = document.querySelector('.sub-text');
                file_name = file.name;
                

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
                            display_info(file_name, result, keys[0], totalPages, activePdfInstance);

                            if (keys.length > 1) {
                                pageTypeContainer.addEventListener('change', function(e) {
                                    if (e.target.name === 'page_type') {
                                        display_info(file_name, result, e.target.value, totalPages, activePdfInstance);
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
                            activePdfInstance = pdf; // Save PDF instance reference globally inside file scope
                            
                            // Execute layout only after promise resolves
                            loadShopItemsAndRender(pdf_pages);
                        }).catch(function(err) {
                            console.error("PDF parsing failed:", err);
                            activePdfInstance = null;
                            loadShopItemsAndRender(1); // Error fallback
                        });
                    };
                    reader.readAsArrayBuffer(file);
                    sub_text.style.display = 'none';
                    main_text.innerHTML = `Selected: ${file_name}`;
                    main_text.style.color = 'green';
                } else {
                    // Images, text documents, docx fallbacks default cleanly to 1 page
                    alert('Not a pdf file.')
                    this.value='';
                    return;
                }
            }
        });

        // Show loading overlay on form submission
        document.querySelector('.up-form').addEventListener('submit', async function(e) {
            e.preventDefault()
            let cart_id = document.querySelector('#cart_id').value;
            let start_page = Number(document.querySelector('#pageStart').value);
            let end_page = Number(document.querySelector('#pageEnd').value);
            let quantity = Number(document.querySelector('#hiddenQuantity').value);

            if (start_page < 1 || start_page > end_page || end_page > pdf_pages){
                alert('Page range invalid');
                return;
            }
            if (quantity < 1){
                alert('Copies should be more than 0');
                return;
            }

            file = await extractPageRange(file, start_page, end_page)
            const cleanFileName = file_name.replace(/\.pdf$/i, '');
            const upload_name = `uploads/${cart_id}/${cleanFileName}_${start_page}_to_${end_page}.pdf`
            await upload_to_aws(upload_name, file, cart_id);
            document.querySelector('#display_name').value = `${cleanFileName}.pdf`;
            document.querySelector('#file_name').value = upload_name;
            e.target.submit();
        });
    }
});

async function extractPageRange(file, startPage, endPage) {
    // Load original PDF
    const arrayBuffer = await file.arrayBuffer();
    const srcDoc = await PDFLib.PDFDocument.load(arrayBuffer);
    const slicedDoc = await PDFLib.PDFDocument.create();

    // Create array of 0-based page indices
    const pageIndices = [];
    for (let i = startPage - 1; i < endPage; i++) {
        pageIndices.push(i);
    }

    // Copy selected pages into the new document
    const copiedPages = await slicedDoc.copyPages(srcDoc, pageIndices);
    copiedPages.forEach((page) => slicedDoc.addPage(page));

    // Save as binary buffer and wrap in a new File object
    const pdfBytes = await slicedDoc.save();
    return new File([pdfBytes], file.name, { type: 'application/pdf' });
}

async function upload_to_aws(filename, file, cart_id){
    try {
        const response = await fetch(`api/get_presigned_upload_url?filename=${filename}&cart_id=${cart_id}`, {
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch upload URL from backend');
        }

        const data = await response.json();
        if (data.status) {
            alert('File already in cart');
            document.querySelector('#doc').value = '';
            return;
        }
        const presignedUrl = data.url;
        
        const loading = document.querySelector('.loading-panel');
        const overlay = document.querySelector('.up-config-panel');
        overlay.style.display = 'none';
        loading.style.display = 'flex';
        // Upload the file DIRECTLY to AWS S3 using the presigned URL
        const uploadResponse = await fetch(presignedUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/pdf'
            },
            body: file
        });

        if (uploadResponse.ok) {
            await uploadResponse.text();
            console.log('File successfully uploaded to S3!');

        } else {
            console.error('S3 Upload failed with status:', uploadResponse.status);
        }
    } catch (error) {
        console.log(error)
    }
}

// Migrate from local storage based to session based.
async function get_or_create_user() {
    const uuid = localStorage.getItem('printo_user_id');
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfInput ? csrfInput.value : getCookie('csrftoken');

    try {
        const headers = { 'X-CSRFToken': csrfToken };
        if (uuid) {
            headers['uuid'] = uuid;
        }

        const response = await fetch('/api/user', {
            method: 'POST',
            headers: headers
        });

        if (response.ok) {
            const data = await response.json();
            if (uuid) {
                localStorage.removeItem('printo_user_id');
            }
            
            return data.user_id;
        }
    } catch (error) {
        console.error('User init failed:', error);
    }
}

function display_info(file_name, result, selected_type, pdf_pages, activePdfInstance) {
    // 1. Select the container
    let itemInfoContainer = document.querySelector('.item-info');
    itemInfoContainer.style.display='flex';
    itemInfoContainer.style.flexDirection='column';
    itemInfoContainer.innerHTML = ''; 

    // Data containers
    let is_color = [];
    let is_b2b = [];

    // 2. Extract unique values
    result[selected_type].forEach(arr => {
        if (!is_color.includes(arr.is_color)) {
            is_color.push(arr.is_color);
        }
        if (!is_b2b.includes(arr.is_b2b)) {
            is_b2b.push(arr.is_b2b);
        }
    });
    if (pdf_pages === 1){
        is_b2b = [is_b2b[0]];
    }

    // 3. Build Strings
    
    // --- Color ---
    let color_options = "";
    is_color.forEach((val, index) => {
        let text = val ? "Color" : "Black & White";
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
        
        if (val) {
            b2b_options += `
                <label class="radio" id="b2bRadioLabel">
                    <input ${checked} name="is_b2b" value="${val}" type="radio" />
                    <span class="name">${text}</span>
                </label>`;
        } else {
            b2b_options += `
                <label class="radio">
                    <input ${checked} name="is_b2b" value="${val}" type="radio" />
                    <span class="name">${text}</span>
                </label>`;
        }
    });

    // 4. Inject innerHTML
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
        <div class="row-info" style="display: flex; flex-direction: column; align-items: stretch; gap: 8px; width: 100%;">
            <div style="display: flex; justify-content: center; gap:1rem; align-items: center; width: 100%;">
                <span>Page Orientation:</span>
                <div class="radio-inputs">
                    <label class="radio">
                        <input checked name="is_portrait" value="true" type="radio"/>
                        <span class="name"> Portrait </span>
                    </label>
                    <label class="radio">
                        <input name="is_portrait" value="false" type="radio" />
                        <span class="name"> Landscape </span>
                    </label>
                </div>
            </div>
            
            <!-- ── NESTED BELOW THE BUTTONS INSIDE THE SAME BORDER ── -->
            <div class="preview-stage-wrapper" style="display: none; justify-content: center; align-items: center; margin: 10px auto 5px auto; width: 100%; min-height: 282px;">
                <div id="pdfThumbnailContainer" class="thumbnail-card" style="box-shadow: 0 4px 12px rgba(0,0,0,0.06); border-radius: 8px; overflow: hidden; background: #fff; border: 1px solid rgba(0,0,0,0.05); position: relative;">
                    <canvas id="preview-thumbnail-canvas" style="display: block; max-width: 100%;"></canvas>
                </div>
            </div>
        </div>

        <div class="row-info" id="printStyleRow">
            <span>Print Style:</span><br>
            <div class="radio-inputs">
                <label class="radio-option">
                    <input type="radio" name="duplex_setting" value="long-edge" checked>
                    <div class="option-card-content">
                        <span class="option-title">Book Style</span>
                        <span class="option-subtitle"><strong>Standard notes & PDFs</strong></span>
                    </div>
                </label>

                <label class="radio-option">
                    <input type="radio" name="duplex_setting" value="short-edge">
                    <div class="option-card-content">
                        <span class="option-title">Notepad Style</span>
                        <span class="option-subtitle"><strong>For PPT slides</strong></span>
                    </div>
                </label>
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

    // --- Live Event Observers for Preview Synchronization ---
    if (activePdfInstance) {
        const getFormOrientation = () => {
            const selected = itemInfoContainer.querySelector('input[name="is_portrait"]:checked');
            return selected ? selected.value : "true";
        };

        const applyColorFilter = () => {
            const selectedColor = itemInfoContainer.querySelector('input[name="is_color"]:checked');
            const canvas = document.getElementById('preview-thumbnail-canvas');
            if (canvas && selectedColor) {
                canvas.style.filter = selectedColor.value === "true" ? 'none' : 'grayscale(100%) contrast(110%)';
            }
        };

        const triggerThumbnailRefresh = () => {
            const startPageInput = document.getElementById('pageStart');
            const targetPage = startPageInput ? (parseInt(startPageInput.value, 10) || 1) : 1;
            
            if (targetPage >= 1 && targetPage <= pdf_pages) {
                updateLiveThumbnail(activePdfInstance, targetPage, getFormOrientation(), applyColorFilter);
            }
        };

        // Render initial presentation frame layout
        triggerThumbnailRefresh();

        // Attach thumbnail refresh on orientation change
        itemInfoContainer.querySelectorAll('input[name="is_portrait"]').forEach(radio => {
            radio.addEventListener('change', triggerThumbnailRefresh);
        });

        // Attach dynamic color filter toggles
        itemInfoContainer.querySelectorAll('input[name="is_color"]').forEach(radio => {
            radio.addEventListener('change', applyColorFilter);
        });

        const pageStartInput = document.getElementById('pageStart');
        if (pageStartInput) {
            pageStartInput.addEventListener('input', triggerThumbnailRefresh);
        }
    }

    // --- Dynamic Print Style & Side Auto-Toggle Engine ---
    const printStyleRow = itemInfoContainer.querySelector('#printStyleRow');
    const b2bRadioLabel = itemInfoContainer.querySelector('#b2bRadioLabel'); 
    const startInput = itemInfoContainer.querySelector('#pageStart');
    const endInput = itemInfoContainer.querySelector('#pageEnd');
    
    const evaluatePrintStyleVisibility = () => {
        if (!printStyleRow) return;
        
        // 1. Compute live targeted printed page count span
        const startPage = startInput ? (parseInt(startInput.value, 10) || 1) : 1;
        const endPage = endInput ? (parseInt(endInput.value, 10) || 1) : 1;
        const activePagesSpan = (endPage - startPage) + 1;
        
        // 2. Hide Back to Back option if single page
        if (activePagesSpan === 1) {
            const singleSideRadio = itemInfoContainer.querySelector('input[name="is_b2b"][value="false"]');
            if (singleSideRadio && !singleSideRadio.checked) {
                singleSideRadio.checked = true;
            }
            if (b2bRadioLabel) b2bRadioLabel.style.display = 'none';
        } else {
            if (b2bRadioLabel) b2bRadioLabel.style.display = ''; 
        }

        // 3. Re-evaluate target selections
        const selectedSide = itemInfoContainer.querySelector('input[name="is_b2b"]:checked');
        const selectedView = itemInfoContainer.querySelector('input[name="is_portrait"]:checked');
        
        // Check for B2B (true) AND Landscape (false)
        const isB2BAndLandscape = selectedSide && selectedView && selectedSide.value === "true" && selectedView.value === "false";
        
        // 4. Print Style row visibility rule
        if (isB2BAndLandscape && activePagesSpan >= 2) {
            printStyleRow.style.display = 'flex';
        } else {
            printStyleRow.style.display = 'none';
        }
    };

    // Run evaluate sequence instantly on initialization parameters
    evaluatePrintStyleVisibility();

    // Listen for side configuration toggles (Single Side / B2B)
    itemInfoContainer.querySelectorAll('input[name="is_b2b"]').forEach(radio => {
        radio.addEventListener('change', evaluatePrintStyleVisibility);
    });

    // Listen for orientation toggles (Portrait / Landscape)
    itemInfoContainer.querySelectorAll('input[name="is_portrait"]').forEach(radio => {
        radio.addEventListener('change', evaluatePrintStyleVisibility);
    });

    // Listen for page range adjustments
    if (startInput) startInput.addEventListener('input', evaluatePrintStyleVisibility);
    if (endInput) endInput.addEventListener('input', evaluatePrintStyleVisibility);
}

function updateLiveThumbnail(pdf, pageNumber, forcedPortrait, callback) {
    const canvas = document.getElementById('preview-thumbnail-canvas');
    const container = document.getElementById('pdfThumbnailContainer');
    const wrapper = document.querySelector('.preview-stage-wrapper');
    
    if (!pdf || !canvas) return;
    if (wrapper) wrapper.style.display = 'flex'; 

    pdf.getPage(pageNumber).then(function(page) {
        // 1. Force rotation = 0 to match SumatraPDF's `disable-auto-rotation`
        const baseViewport = page.getViewport({ scale: 1, rotation: 0 });
        
        const isPortraitBool = forcedPortrait === "true";

        // 2. Set Sheet Frame Dimensions (A4 Ratio Box)
        const targetW = isPortraitBool ? 200 : 282;
        const targetH = isPortraitBool ? 282 : 200;
        
        // 3. Fit Content to Sheet (Matches scaling_logic = "shrink")
        const dpr = window.devicePixelRatio || 1;
        const fitScale = Math.min(targetW / baseViewport.width, targetH / baseViewport.height);
        
        const finalViewport = page.getViewport({ 
            scale: fitScale * dpr,
            rotation: 0
        });

        // 4. Set Canvas Resolution
        canvas.width = finalViewport.width;
        canvas.height = finalViewport.height;
        
        const displayW = finalViewport.width / dpr;
        const displayH = finalViewport.height / dpr;
        
        canvas.style.width = `${displayW}px`;
        canvas.style.height = `${displayH}px`;

        // 5. Center Canvas inside Sheet Frame
        if (container) {
            container.style.width = `${targetW}px`;
            container.style.height = `${targetH}px`;
            
            canvas.style.position = 'absolute';
            canvas.style.left = `${(targetW - displayW) / 2}px`;
            canvas.style.top = `${(targetH - displayH) / 2}px`;
        }

        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);

        page.render({ canvasContext: context, viewport: finalViewport }).promise.then(() => {
            if (typeof callback === 'function') callback();
        });
    }).catch(err => console.error("Thumbnail rendering engine execution dropped:", err));
}

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
}

function calculate_distance(user_lat, user_long, shop_lat, shop_long){
    let distance = (shop_long-user_long)**2 + (shop_lat-user_lat)**2 ;
    return distance;
}

function calculate_real_distance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c; 
}
