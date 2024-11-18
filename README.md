# Bangladesh Railway Fare List

Easily check train schedules, seat fares, and even view route maps for trains across Bangladesh. You can try it out here: **[https://bdrailway.vercel.app](https://bdrailway.vercel.app)**.

![Bangladesh Railway Image](https://github.com/nishatrhythm/Bangladesh-Railway-Train-and-Fare-List/blob/main/images/link_share_image.png)

## What You Can Do

- **Select Stations:** Choose your origin and destination from easy dropdowns.
- **See Fares Instantly:** Get quick fare estimates between selected stations, including VAT details.
- **Find Train Schedules:** View a list of available trains between the stations, with departure/arrival times and days they run.
- **View Routes on a Map:** For some routes, you can see the journey visualized on an interactive map to help plan your trip.
- **Responsive for All Devices:** Works smoothly on both desktop and mobile.

## Tech Behind It

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Flask (Python)
- **Map Integration:** Leaflet.js with GeoJSON for route maps
- **Data:** JSON files for stations, fares, and schedules

---

## CHANGELOG (What's New)

### 2024-11-19
- **New Features**:
  - Integrated interactive maps for select routes to enhance user experience.
- **Improvements**:
  - Enhanced responsiveness and user experience across devices.
  - 
### 2024-11-16
- **New Features**:
  - Enhanced animations for a more intuitive user interface.
- **Improvements**:
  - Added new train data and optimized overall performance.
  - Switched from `orjson` to `ujson` for better deployment compatibility.
  - Improved responsiveness of web components for the better user experience.

### 2024-11-15
- **New Features**:
  - Added a train list feature displaying available trains between selected stations, including departure times and days of operation.
- **Improvements**:
  - Enhanced responsiveness and user experience across devices.
  - Improved table responsiveness for mobile devices.
  - Sorted the train list table by departure time for easier navigation.
  - Updated the design scheme.
- **Bug Fixes**:
  - Corrected the station name containing apostrophe.
    
### 2024-11-12
- **Improvements**:
  - Design scheme updated for better user interface consistency.
  - Added new metadata for SEO optimization.

### 2024-11-11
- **Initial Release**:
  - Launched with basic route search and fare display functionalities.
    
---
