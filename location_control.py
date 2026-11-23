"""An explicit browser geolocation button; no polling or saved location history."""

import streamlit as st


_location_button = st.components.v2.component(
    "library_location",
    html='<button type="button">Use my current location</button><p role="status" aria-live="polite"></p>',
    css="""
        button { width:100%; padding:0.55rem; border:1px solid #E8D8BD;
            border-radius:8px; background:var(--st-background-color, white);
            color:var(--st-text-color, #432818); font:inherit; cursor:pointer; }
        button:disabled { opacity:0.6; cursor:wait; }
        button:focus-visible { outline:2px solid #6F1D1B; outline-offset:2px; }
        p { margin:0.4rem 0; font-size:0.85rem; color:var(--st-text-color, #432818); }
    """,
    js="""
        export default function({parentElement, setTriggerValue}) {
            const button = parentElement.querySelector('button');
            const status = parentElement.querySelector('[role="status"]');
            let active = true;
            button.onclick = () => {
                if (!window.isSecureContext || !navigator.geolocation) {
                    status.textContent = 'Location requires HTTPS or localhost. You can choose a starting point on the map.';
                    return;
                }
                button.disabled = true;
                status.textContent = 'Waiting for location permission…';
                navigator.geolocation.getCurrentPosition(position => {
                    if (!active) return;
                    button.disabled = false;
                    status.textContent = 'Location received.';
                    setTriggerValue('position', {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    });
                }, error => {
                    if (!active) return;
                    button.disabled = false;
                    status.textContent = error.code === 1
                        ? 'Location permission was denied. Choose your starting point on the map.'
                        : 'Could not get your location. Try again or choose a starting point on the map.';
                }, {enableHighAccuracy:true, timeout:12000, maximumAge:60000});
            };
            return () => { active = false; button.onclick = null; };
        }
    """,
)


def location_button(on_position_change):
    return _location_button(key="route_location", on_position_change=on_position_change)
