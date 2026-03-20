# Quantum Key Distribution (QKD) Simulation Dashboard

A modular, web-based Graphical User Interface (GUI) engineered with Django to simulate, analyze, and visualize Quantum Key Distribution (QKD) protocols. The application currently features a comprehensive implementation of the **BBM92** protocol, simulating both Quantum Bit Error Rate (QBER) and Secret Key Rate (SKR) across diverse physical channels (Fiber and Free-Space Optics).

The architecture is explicitly designed to be extensible, strictly decoupling the mathematical simulation logic from the front-end web routing. This allows researchers and developers to iteratively integrate new quantum protocols without dismantling the existing web topology.

---

## 🛠️ 1. Technology Stack

* **Backend Framework:** Django (Python)
* **Scientific Computation:** NumPy, SciPy
* **Data Visualization:** Matplotlib (configured with the headless `'Agg'` backend for thread-safe server rendering)
* **Frontend:** Vanilla HTML5/CSS3 enhanced via Django Template Inheritance

---

## 🚀 2. Installation & Setup

To ensure dependency isolation and prevent version conflicts, the application must be executed within a Python Virtual Environment.

### Prerequisites
* Python 3.10 or higher
* Git (optional, for version control)

### Environment Initialization

1. **Navigate to the workspace root:**
   ```bash
   cd ankush_opticsLab
   ```

2. **Establish a Virtual Environment:**
   Run the following command to generate an isolated Python environment directory named `.venv`.
   ```bash
   python -m venv .venv
   ```

3. **Activate the Environment:**
   * **Linux/macOS:**
     ```bash
     source .venv/bin/activate
     ```
   * **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

4. **Install Dependencies:**
   With the environment active (indicated by `(.venv)` in your terminal prompt), install the required scientific and web dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ 3. Execution Instructions

1. Verify your virtual environment is active.
2. Initialize the Django development server:
   ```bash
   python manage.py runserver
   ```
3. Access the application interface by navigating to the following URL in your web browser:
   **http://127.0.0.1:8000/index**

*To gracefully terminate the server, execute `CTRL + C` in the active terminal.*

---

## 📁 4. Project Architecture

The codebase adheres to a modular Django app structure, ensuring long-term maintainability.

```text
ankush_opticsLab/
│
├── qkd_gui/                   # Project-level Django configuration
│   ├── settings.py            # Global settings, installed apps, and middleware
│   └── urls.py                # Root URL dispatcher
│
├── protocols/                 # Primary Application Module
│   ├── simulators/            # Core Scientific Engine
│   │   ├── bbm92.py           # BBM92 mathematical logic and plotting definitions
│   │   └── __init__.py        # Package initializer
│   │
│   ├── templates/             # Presentation Layer
│   │   ├── base.html          # Global layout, CSS root variables, and Navigation
│   │   ├── landing_page.html  # Welcome interface
│   │   └── bbm92.html         # Protocol-specific parameter dashboard
│   │
│   ├── views.py               # Controller layer: Processes HTTP POSTs, orchestrates physics modules, renders Base64 plots
│   └── urls.py                # Dynamic route handler (e.g., /dashboard/<protocol_name>)
│
├── manage.py                  # Django administrative script
└── requirements.txt           # Environment dependency snapshot
```

---

## 🔌 5. System Extension: Adding New Protocols

The dashboard is built fundamentally around dynamic routing. Extending the application to simulate a new protocol (e.g., **BB84**) requires minimal configuration.

### Phase 1: Integrate the Mathematical Module
1. Navigate to `protocols/simulators/` and create your new Python script (e.g., `bb84.py`).
2. **Crucial Implementation Rules:**
   * **Keyword Argument Propagation:** Ensure all plotting/execution functions accept `**kwargs` so the web interface can organically pass arbitrary parameters without raising `TypeError`. (e.g., `def plot_bb84_skr(mu=0.1, **kwargs):`)
   * **Execution Guards:** Any standalone testing logic or terminal plotting *must* be encapsulated within an `if __name__ == "__main__":` block. If omitted, the functions will execute automatically during Django's import phase, halting the web server.

### Phase 2: Formulate the UI Template
1. Duplicate an existing dashboard layout (e.g., `protocols/templates/bbm92.html`) and rename it `bb84.html`.
2. Modify the HTML form inputs (`<input ... name="parameter_name">`) to align to the physical parameters required by your new protocol. Ensure the `name=` attribute precisely corresponds to the kwargs expected by your python definition.

### Phase 3: Update the Controller (`views.py`)
Open `protocols/views.py` and register the new module within the `dashboard` view function.

1. **Modify the safety boundary:**
   ```python
   # Change from:
   # if protocol_name != 'bbm92':
   
   # Change To:
   if protocol_name not in ['bbm92', 'bb84']:
       raise Http404("Protocol not implemented yet.")
   ```
2. **Import and Route the Logic:**
   ```python
   from .simulators import bbm92, bb84 # Import your new script
   
   if protocol_name == 'bbm92':
       simulator = bbm92
   elif protocol_name == 'bb84':
       simulator = bb84
   ```

### Phase 4: Interface Navigation
Finally, expose the new feature to the user. Edit `protocols/templates/base.html` and append the new route to the navigation sidebar:
```html
<a href="{% url 'dashboard' protocol_name='bb84' %}">BB84 Simulation</a>
```

---

## 🎨 6. UI/UX Customization Guide

* **Global Styling (CSS):** The platform utilizes semantic CSS variables defined within `protocols/templates/base.html`. Altering properties like `--primary: #4a154b;` will universally update the color scheme across all protocols.
* **Component Rendering:** Matplotlib charts are rendered completely headless on the server using `matplotlib.use('Agg')`. They are temporarily cached in an `io.BytesIO()` buffer, encoded into Base64 UTF-8 strings, and injected directly into the HTML `<img>` tags. This eliminates the necessity of storing physical `.png` files on the server's hard drive, optimizing concurrent user operations.

---

## ⚠️ 7. Troubleshooting & Best Practices

* **Port 8000 Already in Use:** If Django refuses to boot, another service is occupying the port. Terminate the blocking process or start Django on an alternate port: `python manage.py runserver 8080`.
* **ModuleNotFoundError:** Indicates missing dependencies. Verify your virtual environment `(.venv)` is visibly active in your shell and execute `pip install -r requirements.txt`.
* **NoReverseMatch Error:** This occurs when Django attempts to build a parameterized URL without arguments. Ensure any `{% url 'dashboard' %}` tags in your templates explicitly include the target parameter (e.g., `{% url 'dashboard' protocol_name='bbm92' %}`).
