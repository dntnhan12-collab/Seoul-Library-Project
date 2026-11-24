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
- `main.py` coordinates the data and UI using an injected `LibraryDataSource`: it loads cleaned rows, creates the manager, applies search and district filters, updates map selection, and requests summary/chart results. The entry point chooses `CsvLibraryDataSource`.
- `services/contracts.py` defines two small protocols: `LibraryDataSource.load()` and `LibraryFilter.matches(library)`.
- `services/data_sources.py` implements CSV and in-memory DataFrame sources. `services/data_manager.py` uses the source contract, converts latitude and longitude to numbers, and removes rows missing required values. `services/search.py` provides keyword search and district filtering. `services/analyzer.py` calculates library and district counts.
- `app.py` renders the Streamlit interface, map, library information, summary metrics, and district chart.
- `services/routing.py` validates coordinates, retrieves walking routes from OSRM, and builds browser links for Naver transit directions.
- `location_control.py` provides the browser location button. It requests permission only when clicked, then starts walking directions or navigates to Naver with both endpoints.
- `tests/test_routing.py` checks route response handling, coordinate validation, error messages, and preservation of the starting point in Naver links.
- `tests/test_library_contracts.py` checks interchangeable data sources and filters, independent data snapshots, and the cleaning/model/search pipeline.

Data flow: injected data source → cleaned DataFrame → `LibraryManager` → `Library` objects → search/filter → map, details, metrics, and chart.

## SOLID principles demonstrated

The project demonstrates all five principles through its data-loading and filtering boundaries:

- **Single Responsibility (S):** `data_sources.py` handles data access, `data_manager.py` cleans rows, `analyzer.py` calculates statistics, `search.py` filters libraries, and `app.py` renders the interface.
- **Open/Closed (O):** A new filter implements `LibraryFilter.matches()` and can be passed to `filter_libraries()` without changing the shared filtering function. A new data source can likewise implement `load()` without changing the cleaning logic.
- **Liskov Substitution (L):** `CsvLibraryDataSource` and `DataFrameLibraryDataSource` satisfy the same behavioral contract: return independent snapshots with the library CSV columns, support repeated reads, and leave cleaning to the consumer. Either can feed the same cleaning/model/search pipeline. `KeywordFilter` and `DistrictFilter` both accept a `Library`, return a repeatable boolean, and do not mutate the library. Their matching criteria differ, but the consumer's assumptions remain valid. Contract tests exercise both implementations, including empty data and repeated calls.
- **Interface Segregation (I):** Data cleaning needs only `LibraryDataSource.load()`; filtering needs only `LibraryFilter.matches(library)`. These are separate one-method protocols. A read-only source does not need save/delete/search methods, and a filter does not need data-loading methods. Tests use minimal objects with only the method their consumer requires.
- **Dependency Inversion (D):** `main(data_source)` and `get_cleaned_library_data(source)` depend on the `LibraryDataSource` abstraction. The executable entry point constructs and injects `CsvLibraryDataSource`; the cleaning service never constructs a CSV reader or knows a file path. Tests inject a DataFrame source or a minimal fake without patching the CSV reader. `filter_libraries()` similarly consumes the `LibraryFilter` abstraction.

These protocols use Python's structural typing: an object with the required method and behavior can be supplied without inheriting from the protocol. Type hints alone do not enforce behavior at runtime; the contract tests verify the shared guarantees.

For example, use an existing table through the same processing code:

```python
from services.data_manager import get_cleaned_library_data
from services.data_sources import DataFrameLibraryDataSource

# existing_dataframe has the same columns as data/seoul_library_english.csv.
libraries = get_cleaned_library_data(DataFrameLibraryDataSource(existing_dataframe))
```

## Dashboard features

- Search suggestions appear while typing a library name; users can select a suggestion to show that library's information and location.
- Filter by district, or use **Find** and **Reset** to apply or clear a search.
- Browse library locations on an interactive map and click a marker to inspect a library.
- View total library and district counts, result count, library details, and a bar chart of libraries by district.
- The **Directions** controls appear directly below the map. Select a library and travel mode, then press **Find route from my location**.
- **Walking** gets your location and draws the route directly on this map, with distance and estimated time. Only the user marker, selected library, and route are displayed while a route is active. **Clear route** restores the library search results.
- **Bus / subway (Naver Map)** gets your location on the dashboard, then opens Naver in a separate browser tab with both endpoints filled in. No mobile app is required. The separate tab avoids Naver's restriction on embedded pages.

## Directions

No API key or additional CSV is required. Walking uses the [FOSSGIS OSRM foot service](https://routing.openstreetmap.de/about.html), intended for light use. Requests are limited to one per second per app process.

Location requires permission and HTTPS or localhost. The walking action shares endpoints with OSRM/FOSSGIS; the transit action shares endpoints with Naver. If location access fails, the app reports the error without opening Naver. The transferred location is a snapshot, not continuous GPS tracking. Browser shortcuts may need updating if Naver changes its URL format.

No blank tab opens while location permission is pending. If the browser blocks the directions tab after GPS completes, the same button changes to **Open directions**. Click it to open the prepared route without requesting location again.

To refresh your location or recalculate a walking route, press **Find route from my location** again. Distances and times describe the route as calculated, not live progress. The app does not automatically reroute or draw bus/subway lines on the dashboard. GPS accuracy depends on the device and browser; a phone usually provides better positioning than a desktop computer.

Library details are rendered as escaped text with wrapping to preserve spacing and special characters. Missing spaces in the CSV's affected closed-day descriptions have been corrected.

## Validation

Run the data-source/filter contract tests and routing checks without calling external services:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

With Node.js installed, run `node tests/location_control.test.cjs` to check the browser navigation logic using simulated location and popup callbacks.

For a manual check, select a library, choose **Walking**, allow location access, and confirm the route and two markers appear. Then select **Bus / subway (Naver Map)** and press the same button to confirm Naver opens with the starting point and destination. Browser location and navigation require a browser check beyond the automated tests.
