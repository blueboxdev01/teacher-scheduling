# Setup & Run — Teacher Scheduling

## Quick Start

### 1. Install dependencies
```bash
pip install flask
```

### 2. Start the server
```bash
python tools/app.py
```
This initializes the database (`.tmp/scheduler.db`) and starts the server at **http://localhost:5000**.

### 3. Open the app
Navigate to [http://localhost:5000](http://localhost:5000) in your browser.

## Seed Sample Data (Optional)
To populate with 5 example teachers and 4 classrooms:
```bash
python tools/scheduler_db.py --seed
```
Then restart the server.

## Usage
1. **Add Teachers** — Go to the Teachers tab, enter name/email/color, click Add
2. **Add Classrooms** — Go to the Classrooms tab, enter name/capacity, click Add
3. **Generate** — On the Schedule tab, click "Generate Schedule"
4. **Review** — Browse days using the day tabs, filter by teacher or classroom
5. **Override** — Click any cell to manually assign/change a teacher
6. **Export** — Click "Export CSV" or use Print for PDF output

## Reset
Delete `.tmp/scheduler.db` and restart the server to start from scratch.
