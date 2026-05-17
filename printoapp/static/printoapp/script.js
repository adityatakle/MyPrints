document.addEventListener('DOMContentLoaded', function() {
    const heading = document.querySelector('.shops-container');
    const title = document.querySelector('#doc');
    if (heading) {
        let user_id = localStorage.getItem('printo_user_id');
        if (!user_id){

            create_user();
        
        }
        else{
            check_user(user_id);
        }

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
                    <button type="submit" ${btn_type} name="shop_id" value="${shop.id}" class="shops_submit">
                        <div class="shop-header">
                            <span class="status-badge status-${status}">${isClosed ? 'Closed' : 'Open Now'}</span>
                        </div>
                        <span class="shop-name">${shop.name}</span>
                        <div class="shop-meta">
                            ${shop.location}, ${shop.landmark}<br>
                            ${shop.city}, ${shop.state}
                        </div>
                    </button>
                    <div class='shop_footer'>
                        <span class="time-info">${status_info}</span>
                        <a href="https://maps.google.com/?q=${shop.latitude},${shop.longitude}" target="_blank">
                            <img src="${window.PIN_ICON}" alt="Map Pin">
                        </a>
                    </div>
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
                let shop_id = document.querySelector('#shop_id')
                shop_id = shop_id.value;
                let main_text = document.querySelector('.main-text');
                let sub_text = document.querySelector('.sub-text');
                file_ext = this.files[0].name.slice(-4);
                let file_name = this.files[0].name.slice(0,-4);
                if (file_name.length > 10){
                    file_name = `${file_name.slice(0,6)}...` 
                }
                sub_text.style.display = 'none';

                main_text.innerHTML = `Selected: ${file_name}${file_ext}`;
                main_text.style.color = 'green';
                // ... Inside your fetch block ...
                fetch(`/api/item_list/${shop_id}`)
                .then(response => response.json())
                .then(result => {
                    // 1. Select the Page Type Container (Rename variable for clarity)
                    let pageTypeContainer = document.querySelector('.page_type');
                    pageTypeContainer.style.display = 'flex';
                    pageTypeContainer.style.flexDirection = "column";

                    // 2. Build Page Type Dropdown
                    let page_types_innerHTML = ``;
                    for (let i = 0; i < Object.keys(result).length; i++) {
                        page_types_innerHTML += `<option value="${Object.keys(result)[i]}">${Object.keys(result)[i]}</option>`;
                    }
                    pageTypeContainer.innerHTML = `<div class='row-info'>
                                                        <span>Page type: </span>   
                                                        <select name='page_type' id='page_type' class='form-control'> ${page_types_innerHTML} </select>
                                                        </div>`;

                    // 3. Call display_info to fill it
                    display_info(file_name, result, Object.keys(result)[0]);

                    // 4. Add Listener (Check length so we don't break on single items)
                    if (Object.keys(result).length > 1) {
                        pageTypeContainer.addEventListener('change', function(e) {
                            if (e.target.id == 'page_type') {
                                display_info(file_name, result, e.target.value);
                            }
                        });
                    }
                });
            }
        })
        // Show loading overlay on form submission
        document.querySelector('.up-form').addEventListener('submit', function() {
            const loading = document.querySelector('.loading-panel');
            const overlay = document.querySelector('.up-config-panel');
            overlay.style.display = 'none';
            loading.style.display = 'flex';
        });
    }
});

function create_user(){
    fetch("/api/create_user") // Added absolute path
    .then(response => response.json())
    .then(result => {
        let user_id = result.user_id;
        localStorage.setItem('printo_user_id', user_id);
        
        // Safely set inputs if they exist on the page
        const idField = document.querySelector('#user_id');
        if (idField) idField.value = user_id;
        
        const userLabel = document.querySelector('#current_user');
        if (userLabel) userLabel.innerHTML = user_id;
    });
}

function check_user(uuid){
    fetch(`/api/check_user/${uuid}`) // Added absolute path
    .then(response => response.json())
    .then(result => {
        if (result.status === 'Create new'){
            create_user();
        } else {
            // CRITICAL FIX: If user exists, you MUST put their ID in the hidden form field!
            const idField = document.querySelector('#user_id');
            if (idField) {
                idField.value = uuid;
            }
        }
    });
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
    is_color.forEach(val => {
        let text = val ? "Color" : "Black & White";
        color_options += `<option value="${val}">${text}</option>`;
    });

    // --- B2B ---
    let b2b_options = "";
    is_b2b.forEach(val => {
        let text = val ? "Back to Back" : "Single Side";
        b2b_options += `<option value="${val}">${text}</option>`;
    });    

    // 4. Inject everything at once using innerHTML
    // This is faster and cleaner than 3 separate appends
    itemInfoContainer.innerHTML = `
        <div class="row-info">
            <span>Print Color:</span>
            <select name='is_color' id="color-select" class="form-control">${color_options}</select>
        </div>
        <div class="row-info">
            <span>Print Side:</span>
            <select id="b2b-select" name='is_b2b' class="form-control">${b2b_options}</select>
        </div>
        <div class="row-info">
            <span>Rename file:</span>
            <input type="text" name="rename-file" class="form-control" placeholder=${file_name} maxlength="255" pattern="[A-Za-z0-9_]+">
        </div>
        <div class="row-info">
            <span>Copies:</span>
            <input type="number" class="form-control" name="quantity" min="1" max="20" placeholder="1">
        </div>
        <div class="row-info">
            <button id='submit-btn' type='submit'> Add to cart</button>
        </div>`
    let submit_btn = itemInfoContainer.querySelector('#submit-btn');
    submit_btn.style.marginTop ='20px';
    submit_btn.style.borderRadius='10px';
};

function getPreciseLocation(callback) {
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
    );
};

function calculate_distance(user_lat, user_long, shop_lat, shop_long){
    let distance = (shop_long-user_long)**2 + (shop_lat-user_lat)**2 ;
    return distance;
};


// maps link with route https://www.google.com/maps/dir/?api=1&destination=${lat},${long}&travelmode=walking
// maps link of a place https://www.google.com/maps/search/?api=1&query=${lat},${long}