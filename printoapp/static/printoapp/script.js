document.addEventListener('DOMContentLoaded', function() {
    const heading = document.querySelector('.shops-container');
    const title = document.querySelector('#doc');
    if (heading) {
        get_or_create_user();

        getPreciseLocation((location) => {
            const shops = JSON.parse(document.getElementById('shops-data').textContent);
            const shopsList = document.getElementById('shops-list');

            // Calculate distances safely
            for (let shop of shops) {
                if (location === 'error' || !shop.latitude) {
                    shop.distance = Infinity;
                } else {
                    shop.distance = calculate_distance(location[0], location[1], shop.latitude, shop.longitude);
                }
            }

            // Sort by distance
            shops.sort((a, b) => a.distance - b.distance);

            let finalHTML = "";
            for (let shop of shops) {
                let isClosed = !shop.is_open;
                let btn_type = isClosed ? 'disabled' : '';
                let status = isClosed ? 'closed' : 'open';
                let status_info = isClosed ? 'Closed now' : 'Open now';

                finalHTML += `
                <div class="shops_container">
                    <div class="shop-header">
                            <span class="status-badge status-${status}">${isClosed ? 'Closed' : 'Open Now'}</span>
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
        });
    }
    if (title){
        const toggleBtn = document.getElementById('catalogueToggle');
        const contentPanel = document.getElementById('catalogueContent');
        
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
                const MAX_SIZE_MB = 40;
                const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

                if (file.size > MAX_SIZE_BYTES) {
                    alert(`File is too large! Max limit is ${MAX_SIZE_MB}MB.`);
                    this.value = "";
                    return;
                }
                let shop_id = document.querySelector('#shop_id');
                shop_id = shop_id.value;
                let main_text = document.querySelector('.main-text');
                let sub_text = document.querySelector('.sub-text');
                let file_ext = this.files[0].name.slice(-4);
                let file_name = this.files[0].name.slice(0,-4);
                if (file_name.length > 10){
                    file_name = `${file_name.slice(0,6)}...` ;
                }
                sub_text.style.display = 'none';

                main_text.innerHTML = `Selected: ${file_name}${file_ext}`;
                main_text.style.color = 'green';
                
                fetch(`/api/item_list/${shop_id}`)
                .then(response => response.json())
                .then(result => {
                    let pageTypeContainer = document.querySelector('.page_type');
                    pageTypeContainer.style.display = 'flex';
                    pageTypeContainer.style.flexDirection = "column";
                    
                    // FIXED 1: Declare the innerHTML string helper first!
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

                    // FIXED 2: Single clear injection. Old select element block removed completely!
                    pageTypeContainer.innerHTML = `
                        <div class='row-info'>
                            <span>Page type: </span>   
                            <div class="radio-inputs"> 
                                ${page_types_innerHTML} 
                            </div>
                        </div>`;

                    display_info(file_name, result, keys[0]);

                    // FIXED 3: Event tracking updated to look for standard input name attributes
                    if (keys.length > 1) {
                        pageTypeContainer.addEventListener('change', function(e) {
                            if (e.target.name === 'page_type') {
                                display_info(file_name, result, e.target.value);
                            }
                        });
                    }
                });
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

function display_info(file_name,result, selected_type) {
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
        <div class="row-info">
            <span>Copies:</span>
            <input type="number" class="form-control" name="quantity" min="1" max="20" placeholder="1">
        </div>
        <div class="row-info">
            <button class="wooden-cart-button" id='submit-btn' type='submit'>
                <svg viewBox="0 0 24 24">
                    <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A.996.996 0 0 0 21.42 4H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"></path>
                </svg>
                <span class="button-text">Add to cart</span>
            </button>
        </div>`;

    let submit_btn = itemInfoContainer.querySelector('#submit-btn');
    submit_btn.style.marginTop ='20px';
    submit_btn.style.borderRadius='10px';
};

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


// maps link with route https://www.google.com/maps/dir/?api=1&destination=${lat},${long}&travelmode=walking
// maps link of a place https://www.google.com/maps/search/?api=1&query=${lat},${long}