# Seoul Public Library Explorer

An interactive Streamlit dashboard for exploring Seoul's public libraries. Search libraries by name or district, view their locations on a map, inspect library details, compare library counts by district, and see summary statistics.

The public dashboard is live at [Seoul Public Library Explorer](https://seoul-library-explorer.streamlit.app/). Its source code is in the public [Seoul-Library-Project GitHub repository](https://github.com/dntnhan12-collab/Seoul-Library-Project).

## Run the dashboard

1. Install Python and Git.
2. Clone the public repository and enter its folder:

   ```powershell
   git clone https://github.com/dntnhan12-collab/Seoul-Library-Project.git
   cd Seoul-Library-Project
   ```

3. Create and activate a virtual environment, then install the dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   If PowerShell blocks activation, allow it for the current terminal only, then activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

4. Start Streamlit:

   ```powershell
   streamlit run main.py
   ```

   Streamlit prints a local address (usually `http://localhost:8501`) in the terminal. Open that address in a browser.

## Data used

The project uses the Seoul Metropolitan Government dataset **Seoul Public Library Status Information** (official Korean title: 서울시 공공도서관 현황정보), published on the [Seoul Open Data Plaza](https://data.seoul.go.kr/dataList/OA-15480/S/1/datasetView.do). The downloaded project data is stored in `data/seoul_library_english.csv`; the team prepared the CSV in English for this application. It contains library names, districts, addresses, contact and operating information, and coordinates.

## Class design and object interactions

- `Library` (`models/library.py`) represents one library record. It stores library details, checks whether a keyword matches the name, district, or address, builds an object from a data row, and returns details for display.
- `LibraryManager` (`models/library_manager.py`) creates `Library` objects from the cleaned DataFrame and provides the collection to the rest of the program.
- `main.py` coordinates the data and UI: it loads cleaned rows, creates the manager, applies search and district filters, updates map selection, and requests summary/chart results.
- `services/data_manager.py` reads the CSV, converts latitude and longitude to numbers, and removes rows missing required values. `services/search.py` provides keyword search and district filtering. `services/analyzer.py` calculates library and district counts.
- `app.py` renders the Streamlit interface, map, library information, summary metrics, and district chart.

In short: CSV → cleaned DataFrame → `LibraryManager` → `Library` objects → search/filter → map, details, metrics, and chart.

## SOLID principles demonstrated

This project focuses on the two SOLID principles most clearly represented in its current code:

- **Single Responsibility (S):** Responsibilities are separated across modules. `data_manager.py` loads and cleans data, `analyzer.py` calculates statistics, `search.py` filters libraries, and `app.py` renders the interface.
- **Open/Closed (O):** `search.py` defines the `LibraryFilter` contract. A new filter can implement `matches()` and be passed to `filter_libraries()` without changing the shared filtering function.

## Dashboard features

- Search suggestions appear while typing a library name; users can select a suggestion to show that library's information and location.
- Filter by district, or use **Find** and **Reset** to apply or clear a search.
- Browse library locations on an interactive map and click a marker to inspect a library.
- View total library and district counts, result count, library details, and a bar chart of libraries by district.
- Select a library, use **Use my current location** or **Choose starting point on map**, and press **Show route** to draw a walking route directly on the map with distance and estimated time.
- Walking is available without an API key. Bus, subway, and combined routes require the ODsay setup below; they remain unavailable until configured.
- The **Open in Naver Map** section also provides an app link for walking or public transit. Naver Map must be installed and allowed to access your location.
- Use **Directions in browser** on a computer or without the app. The destination is filled in; choose the starting point and travel mode in Naver Map. This link initially opens public transit directions.

Directions use the existing library coordinates; no additional CSV is needed. Mobile links follow the [Naver URL Scheme documentation](https://guide-gov.ncloud-docs.com/release-20260820/docs/naveropenapiv3-maps-url-scheme-url-scheme). The browser shortcut may need updating if Naver changes its URL format.

## Routes displayed on the website

Walking uses the [FOSSGIS OSRM foot service](https://routing.openstreetmap.de/about.html), based on OpenStreetMap paths. The app draws the returned geometry rather than a straight line. Time is an estimate, and path coverage depends on OpenStreetMap. If no route is available, the app shows an error without inventing a line. The public service is for light usage: calls are serialized to at most one per second per app process, and the current result is kept only in the user's Streamlit session. Use a dedicated routing service before running a busy or multi-process deployment.

Browser location works on HTTPS or localhost and requires permission. Users can instead enable **Choose starting point on map** and click the map; switch it off to select library markers again. The map's existing locate icon only centers the map; the new **Use my current location** button sets the route origin. Clicking **Show route** sends the selected endpoints to the routing provider. They are not written to project files or shared caches; providers may retain request logs according to their policies.

For bus/subway routes:

1. Register an **ODsay Server API key**, with the outbound IP of the machine running Streamlit. A Web key is not interchangeable with a Server key. Check the provider's plan and access to both `searchPubTransPathT` and `loadLane`.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in `ODSAY_API_KEY`. The real secrets file is ignored by Git. Alternatively set the `ODSAY_API_KEY` environment variable. On Streamlit hosting, use the app's Secrets settings and confirm the host's outbound IP meets ODsay's requirements.
3. Restart Streamlit, select **Bus**, **Subway**, or **Bus + subway**, and click **Show route**.

The adapter requests ODsay's recommended local journey and draws the route geometry from `loadLane`: green for bus and purple for subway. Walking connections are drawn in blue using OSRM; if a connection cannot be routed, it is explicitly reported as missing. Stops and transfer steps appear in **Route details**. The estimate is not a live vehicle arrival forecast. See [ODsay API reference](https://lab.odsay.com/guide/releaseReference) and [Server versus Web key guidance](https://lab.odsay.com/community/boardView?seq=658).

The walking provider has been tested with a real Seoul route. The ODsay adapter has automated response-fixture tests but still needs a live integration check with a configured key.

Run routing checks with `python -m unittest discover -s tests -v`.
