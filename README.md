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
- After selecting a library, use **Open Naver Map app** on a phone for directions from your current location, with public transit, walking, driving, or cycling options. Naver Map must be installed and allowed to access your location.
- Use **Directions in browser** on a computer or without the app. The destination is filled in; choose the starting point and travel mode in Naver Map. This link initially opens public transit directions.

Directions use the existing library coordinates and require no API key or additional dataset. Routes are displayed in Naver Map, outside this dashboard; the dashboard does not collect or store the user's location for these links. Mobile links follow the [Naver URL Scheme documentation](https://guide-gov.ncloud-docs.com/release-20260820/docs/naveropenapiv3-maps-url-scheme-url-scheme). The browser shortcut is verified against Naver's current website and may need updating if Naver changes its URL format.
