document.addEventListener('DOMContentLoaded', function() {
    const heading = document.querySelector('.shop-info');
    const title = document.querySelector('#doc');
    if (heading) {
        let user_id = localStorage.getItem('printo_user_id');
        if (!user_id){
            console.log("No user id. New User!!!")

            fetch("api/create_user")
            .then(response => response.json())
            .then(result => {
                console.log(result);
                let user_id = result.user_id;
                localStorage.setItem('printo_user_id',user_id);
                console.log(`Your user id is ${user_id}`);
                document.querySelector('#user_id').value = user_id;
            })
        
        }
        else{
            console.log(`Your user id is: ${user_id}`);
            document.querySelector('#user_id').value = user_id;
        }
    }
    if (title){
        title.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
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
                console.log(`${main_text.innerHTML}`);
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
                                console.log("Changed Element Value:", e.target.value);
                                display_info(file_name, result, e.target.value);
                            }
                        });
                    }
                });
            }
        })
    }
});


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