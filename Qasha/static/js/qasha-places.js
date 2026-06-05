/**
 * Google Places Autocomplete for Qasha address and search fields.
 * Requires GOOGLE_MAPS_API_KEY in .env and Maps JavaScript API + Places API enabled.
 */
(function () {
    'use strict';

    const ZA = { country: 'za' };

    function component(components, type) {
        const c = components.find(function (x) {
            return x.types.indexOf(type) !== -1;
        });
        return c ? c.long_name : '';
    }

    function parsePlace(place) {
        const parts = place.address_components || [];
        const streetNum = component(parts, 'street_number');
        const route = component(parts, 'route');
        const line = [streetNum, route].filter(Boolean).join(' ').trim();
        return {
            address: line || place.name || '',
            suburb:
                component(parts, 'sublocality_level_1') ||
                component(parts, 'sublocality') ||
                component(parts, 'neighborhood') ||
                '',
            city:
                component(parts, 'locality') ||
                component(parts, 'administrative_area_level_2') ||
                component(parts, 'administrative_area_level_1') ||
                '',
            lat: place.geometry && place.geometry.location ? place.geometry.location.lat() : null,
            lng: place.geometry && place.geometry.location ? place.geometry.location.lng() : null,
            label: place.formatted_address || place.name || '',
        };
    }

    function bindListing(autocomplete, addressEl) {
        const suburbEl = document.getElementById('id_suburb') || document.getElementById('id_home_suburb');
        const cityEl = document.getElementById('id_city') || document.getElementById('id_home_city');
        const latEl = document.getElementById('id_latitude') || document.getElementById('id_home_latitude');
        const lngEl = document.getElementById('id_longitude') || document.getElementById('id_home_longitude');

        autocomplete.addListener('place_changed', function () {
            const place = autocomplete.getPlace();
            if (!place || !place.geometry) {
                return;
            }
            const p = parsePlace(place);
            if (addressEl) {
                addressEl.value = p.address || p.label;
            }
            if (suburbEl && p.suburb) {
                suburbEl.value = p.suburb;
            }
            if (cityEl && p.city) {
                cityEl.value = p.city;
            }
            if (latEl && p.lat != null) {
                latEl.value = p.lat;
            }
            if (lngEl && p.lng != null) {
                lngEl.value = p.lng;
            }
        });
    }

    function bindSuburbCity(autocomplete, suburbEl, cityEl) {
        autocomplete.addListener('place_changed', function () {
            const place = autocomplete.getPlace();
            if (!place) {
                return;
            }
            const p = parsePlace(place);
            if (suburbEl) {
                suburbEl.value = p.suburb || p.city || p.label.split(',')[0].trim();
            }
            if (cityEl && p.city) {
                if (cityEl.tagName === 'SELECT') {
                    const target = p.city.toLowerCase();
                    for (let i = 0; i < cityEl.options.length; i++) {
                        const opt = cityEl.options[i];
                        if (
                            opt.value.toLowerCase() === target ||
                            opt.text.toLowerCase() === target
                        ) {
                            cityEl.value = opt.value;
                            break;
                        }
                    }
                } else {
                    cityEl.value = p.city;
                }
            }
        });
    }

    function bindSearch(autocomplete, inputEl) {
        autocomplete.addListener('place_changed', function () {
            const place = autocomplete.getPlace();
            if (!place) {
                return;
            }
            const p = parsePlace(place);
            inputEl.value = p.city || p.suburb || p.label;
        });
    }

    function attach(inputEl) {
        if (!inputEl || inputEl.dataset.qashaPlacesBound === '1') {
            return;
        }
        if (!window.google || !google.maps || !google.maps.places) {
            return;
        }

        const mode = inputEl.getAttribute('data-qasha-places') || 'search';
        const options = {
            componentRestrictions: ZA,
            fields: ['address_components', 'geometry', 'formatted_address', 'name'],
        };

        if mode === 'listing' || mode === 'home') {
            options.types = ['address'];
        } else if (mode === 'suburb') {
            options.types = ['(regions)'];
        } else {
            options.types = ['(regions)'];
        }

        const autocomplete = new google.maps.places.Autocomplete(inputEl, options);
        inputEl.dataset.qashaPlacesBound = '1';
        inputEl.setAttribute('autocomplete', 'off');

        if (mode === 'listing' || mode === 'home') {
            bindListing(autocomplete, inputEl);
        } else if (mode === 'suburb') {
            const cityEl = document.getElementById(
                inputEl.getAttribute('data-qasha-city-field') || 'city'
            );
            bindSuburbCity(autocomplete, inputEl, cityEl);
        } else {
            bindSearch(autocomplete, inputEl);
        }
    }

    function initAll() {
        document.querySelectorAll('[data-qasha-places]').forEach(attach);
    }

    window.qashaPlacesReady = function () {
        initAll();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            if (window.google && google.maps && google.maps.places) {
                initAll();
            }
        });
    } else if (window.google && google.maps && google.maps.places) {
        initAll();
    }
})();
