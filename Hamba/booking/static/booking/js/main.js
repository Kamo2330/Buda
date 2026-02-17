/**
 * Hamba - Main JS: airport autocomplete, form helpers
 */

document.addEventListener('DOMContentLoaded', function() {

    // ----- Airport autocomplete (home page: From / To) -----
    var originInput = document.getElementById('id_origin');
    var destInput = document.getElementById('id_destination');
    var productTypeInput = document.getElementById('product-type-input');

    function airportSuggestionsUrl(q) {
        return '/airports/search/?q=' + encodeURIComponent(q);
    }

    function setupAirportAutocomplete(input) {
        if (!input) return;

        var wrapper = input.closest('.form-group') || input.parentElement;
        if (!wrapper) return;
        wrapper.style.position = 'relative';

        var list = document.createElement('div');
        list.className = 'airport-suggestions-list';
        list.style.cssText = 'position:absolute;left:0;right:0;top:100%;z-index:1000;background:#fff;border:1px solid #e2e8f0;border-top:none;max-height:220px;overflow-y:auto;display:none;font-size:0.9rem;';
        wrapper.appendChild(list);

        var debounce = null;
        function onInput() {
            var q = (input.value || '').trim().toLowerCase();
            if (productTypeInput && productTypeInput.value !== 'flight') {
                list.style.display = 'none';
                list.innerHTML = '';
                return;
            }
            if (q.length < 1) {
                list.style.display = 'none';
                list.innerHTML = '';
                return;
            }
            clearTimeout(debounce);
            debounce = setTimeout(function() {
                fetch(airportSuggestionsUrl(q))
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        list.innerHTML = '';
                        if (!Array.isArray(data) || data.length === 0) {
                            list.style.display = 'none';
                            return;
                        }
                        data.slice(0, 10).forEach(function(a) {
                            var item = document.createElement('div');
                            item.style.cssText = 'padding:8px 12px;cursor:pointer;border-top:1px solid #eee;';
                            item.textContent = (a.city || '') + ' - ' + (a.name || '') + ' (' + (a.code || '') + ')';
                            item.addEventListener('mousedown', function(e) {
                                e.preventDefault();
                                input.value = a.code || a.iata_code || '';
                                list.style.display = 'none';
                                list.innerHTML = '';
                            });
                            list.appendChild(item);
                        });
                        list.style.display = 'block';
                    })
                    .catch(function() {
                        list.style.display = 'none';
                        list.innerHTML = '';
                    });
            }, 150);
        }

        input.addEventListener('input', onInput);
        input.addEventListener('focus', function() {
            if (input.value.trim()) onInput();
        });
        document.addEventListener('click', function(e) {
            if (!wrapper.contains(e.target)) {
                list.style.display = 'none';
            }
        });
    }

    if (originInput) setupAirportAutocomplete(originInput);
    if (destInput) setupAirportAutocomplete(destInput);

    // ----- Trip type: show/hide return date -----
    var returnDateGroup = document.getElementById('return-date-group');
    var returnDateInput = document.getElementById('id_return_date');
    if (returnDateGroup && returnDateInput) {
        document.querySelectorAll('input[name="trip_type"]').forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (this.value === 'oneway') {
                    returnDateGroup.style.display = 'none';
                    returnDateInput.removeAttribute('required');
                } else {
                    returnDateGroup.style.display = 'block';
                    returnDateInput.setAttribute('required', 'required');
                }
            });
        });
        var checked = document.querySelector('input[name="trip_type"]:checked');
        if (checked) checked.dispatchEvent(new Event('change'));
    }

    // ----- Product type buttons (Flights, Buses, etc.) -----
    var searchBtn = document.getElementById('search-button');
    document.querySelectorAll('.product-type-button').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.product-type-button').forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');
            var type = this.getAttribute('data-type') || 'flight';
            if (productTypeInput) productTypeInput.value = type;
            if (searchBtn) {
                if (type === 'flight') searchBtn.textContent = 'Search Flights';
                else if (type === 'bus') searchBtn.textContent = 'Search Buses';
                else if (type === 'stay') searchBtn.textContent = 'Search Accommodations';
                else if (type === 'package') searchBtn.textContent = 'Search Packages';
                else searchBtn.textContent = 'Search';
            }
        });
    });

    // ----- Auto-dismiss alerts -----
    document.querySelectorAll('.alert').forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 300);
        }, 5000);
    });
});
