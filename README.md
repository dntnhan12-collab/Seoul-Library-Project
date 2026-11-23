# Seoul Public Library Explorer

An interactive Streamlit dashboard for exploring Seoul's public libraries. Search by name or district, inspect library details, compare district counts, and find directions from your current location. Walking routes appear on the dashboard; bus and subway journeys open directly in Naver Map's website.

The public dashboard is live at [Seoul Public Library Explorer](https://seoul-library-explorer.streamlit.app/). Its source code is in the public [Seoul-Library-Project GitHub repository](https://github.com/dntnhan12-collab/Seoul-Library-Project).

## Run the dashboard

1. Install Python and Git.
2. Clone the public repository and enter its folder:

   ```powershell
   git clone https://github.com/dntnhan12-collab/Seoul-Library-Project.git
   cd Seoul-Library-Project
   ```

3. Create a virtual environment and install the dependencies (PowerShell / VS Code terminal):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Start Streamlit:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run main.py
   ```

   Streamlit prints a local address (usually `http://localhost:8501`) in the terminal. Open that address in a browser.

   On macOS/Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe` (and `python3` to create the environment). Streamlit 1.64.0 or later is required.

## Data used

The project uses the Seoul Metropolitan Government dataset **Seoul Public Library Status Information** (official Korean title: 서울시 공공도서관 현황정보), published on the [Seoul Open Data Plaza](https://data.seoul.go.kr/dataList/OA-15480/S/1/datasetView.do). The downloaded project data is stored in `data/seoul_library_english.csv`; the team prepared the CSV in English for this application. It contains library names, districts, addresses, contact and operating information, and coordinates.

## Class design and object interactions

- `Library` (`models/library.py`) represents one library record. It stores library details, checks whether a keyword matches the name, district, or address, builds an object from a data row, and returns details for display.
- `LibraryManager` (`models/library_manager.py`) creates `Library` objects from the cleaned DataFrame and provides the collection to the rest of the program.
- `main.py` coordinates the data and UI: it loads cleaned rows, creates the manager, applies search and district filters, updates map selection, and requests summary/chart results.
- `services/data_manager.py` reads the CSV, converts latitude and longitude to numbers, and removes rows missing required values. `services/search.py` provides keyword search and district filtering. `services/analyzer.py` calculates library and district counts.
- `app.py` renders the Streamlit interface, map, library information, summary metrics, and district chart.
- `services/routing.py` validates coordinates, retrieves walking routes from OSRM, and builds browser links for Naver transit directions.
- `location_control.py` provides the browser location button. It requests permission only when clicked, then starts walking directions or navigates to Naver with both endpoints.
- `tests/test_routing.py` checks route response handling, coordinate validation, error messages, and preservation of the starting point in Naver links.

Data flow: CSV → cleaned DataFrame → `LibraryManager` → `Library` objects → search/filter → map, details, metrics, and chart.

## SOLID principles demonstrated

This project focuses on the two SOLID principles most clearly represented in its current code:

- **Single Responsibility (S):** Responsibilities are separated across modules. `data_manager.py` loads and cleans data, `analyzer.py` calculates statistics, `search.py` filters libraries, and `app.py` renders the interface.
- **Open/Closed (O):** `search.py` defines the `LibraryFilter` contract. A new filter can implement `matches()` and be passed to `filter_libraries()` without changing the shared filtering function.

## Dashboard features

- Search suggestions appear while typing a library name; users can select a suggestion to show that library's information and location.
- Filter by district, or use **Find** and **Reset** to apply or clear a search.
- Browse library locations on an interactive map and click a marker to inspect a library.
- View total library and district counts, result count, library details, and a bar chart of libraries by district.
- The **Directions** controls appear directly below the map. Select a library and travel mode, then press **Find route from my location**.
- **Walking** gets your location and draws the route directly on this map, with distance and estimated time. Only the user marker, selected library, and route are displayed while a route is active. **Clear route** restores the library search results.
- **Bus / subway (Naver Map)** opens a separate browser tab, gets your location, and loads Naver with both endpoints filled in. No second button or mobile app is required. The separate tab avoids Naver's restriction on embedded pages.

## Directions

No API key or additional CSV is required. Walking uses the [FOSSGIS OSRM foot service](https://routing.openstreetmap.de/about.html), intended for light use. Requests are limited to one per second per app process.

Location requires permission and HTTPS or localhost. The walking action shares endpoints with OSRM/FOSSGIS; the transit action shares endpoints with Naver. If location access fails, the app reports the error without opening Naver. The transferred location is a snapshot, not continuous GPS tracking. Browser shortcuts may need updating if Naver changes its URL format.

Allow pop-ups for the dashboard if the browser blocks the directions tab. A temporary tab opens immediately on the click while location permission is pending; it closes if location access fails.

To refresh your location or recalculate a walking route, press **Find route from my location** again. Distances and times describe the route as calculated, not live progress. The app does not automatically reroute or draw bus/subway lines on the dashboard. GPS accuracy depends on the device and browser; a phone usually provides better positioning than a desktop computer.

Library details are rendered as escaped text with wrapping to preserve spacing and special characters. Missing spaces in the CSV's affected closed-day descriptions have been corrected.

## Validation

Run the automated routing checks without calling external services:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

With Node.js installed, run `node tests/location_control.test.cjs` to check the browser navigation logic using simulated location and popup callbacks.

For a manual check, select a library, choose **Walking**, allow location access, and confirm the route and two markers appear. Then select **Bus / subway (Naver Map)** and press the same button to confirm Naver opens with the starting point and destination. Browser location and navigation require a browser check beyond the automated tests.
