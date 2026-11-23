"""An explicit browser geolocation button; no polling or saved location history."""

import streamlit as st


_location_button = st.components.v2.component(
    "library_location",
    html='<button type="button" title="Get your location and find a route. Walking endpoints are sent to OSRM/FOSSGIS.">Find route from my location</button><p role="status" aria-live="polite"></p>',
    css="""
        button { width:100%; padding:0.55rem; border:1px solid #E8D8BD;
            border-radius:8px; background:var(--st-primary-color, #6F1D1B);
            color:white; font:inherit; cursor:pointer; }
        button:disabled { opacity:0.6; cursor:wait; }
        button:focus-visible { outline:2px solid #6F1D1B; outline-offset:2px; }
        p { margin:0.4rem 0; font-size:0.85rem; color:var(--st-text-color, #432818); }
        p:empty { display:none; }
    """,
    js="""
        export default function({parentElement, setTriggerValue, data}) {
            const button = parentElement.querySelector('button');
            const status = parentElement.querySelector('[role="status"]');
            button.title = data?.browser_url
                ? 'Get your location and open Naver in a new browser tab with both endpoints.'
                : 'Get your location and find a walking route using OSRM/FOSSGIS.';
            let active = true;
            let pendingTab = null;
            const closePendingTab = () => {
                if (pendingTab && !pendingTab.closed) pendingTab.close();
                pendingTab = null;
            };
            button.onclick = () => {
                if (!window.isSecureContext || !navigator.geolocation) {
                    status.textContent = 'Location requires HTTPS or localhost.';
                    return;
                }
                // Open during the click gesture, before async GPS permission.
                // Navigating this Streamlit frame would be blocked by Naver.
                if (data?.browser_url) {
                    pendingTab = window.open('about:blank', '_blank');
                    if (!pendingTab) {
                        status.textContent = 'Allow pop-ups for this site, then try again.';
                        return;
                    }
                    pendingTab.opener = null;
                    pendingTab.document.title = 'Finding directions';
                    pendingTab.document.body.textContent =
                        'Waiting for your location. Allow location access on the library page.';
                }
                button.disabled = true;
                status.textContent = 'Waiting for location permission…';
                navigator.geolocation.getCurrentPosition(position => {
                    if (!active) return;
                    button.disabled = false;
                    status.textContent = '';
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)
                        || latitude < 33 || latitude > 39 || longitude < 124 || longitude > 132) {
                        closePendingTab();
                        status.textContent = 'Your location must be in South Korea to find a route.';
                        return;
                    }
                    if (data?.browser_url) {
                        if (!pendingTab || pendingTab.closed) {
                            pendingTab = null;
                            status.textContent = 'The directions tab was closed. Click Find route again.';
                            return;
                        }
                        const url = new URL(data.browser_url);
                        url.searchParams.set('slat', String(latitude));
                        url.searchParams.set('slng', String(longitude));
                        url.searchParams.set('stext', 'Starting point');
                        pendingTab.location.replace(url.toString());
                        pendingTab = null;
                    }
                    setTriggerValue('position', {latitude, longitude});
                }, error => {
                    if (!active) return;
                    button.disabled = false;
                    closePendingTab();
                    status.textContent = error.code === 1
                        ? 'Location permission was denied. Enable location access in your browser and try again.'
                        : 'Could not get your location. Check location services and try again.';
                }, {enableHighAccuracy:true, timeout:12000, maximumAge:60000});
            };
            return () => {
                active = false;
                closePendingTab();
                button.onclick = null;
            };
        }
    """,
)


def location_button(on_position_change, browser_url=None):
    return _location_button(
        key="route_location", data={"browser_url": browser_url},
        on_position_change=on_position_change,
    )
