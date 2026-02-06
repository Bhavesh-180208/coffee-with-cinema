// --- Navigation & UI Logic ---

function showLoginModal() {
    document.getElementById('loginModal').classList.remove('hidden');
}

function submitName() {
    const usernameInput = document.getElementById('usernameInput');
    const username = usernameInput.value;

    if (!username) {
        alert("Please enter a name");
        return;
    }

    console.log("Sending name to server:", username); // Debugging line

    fetch('/set_username', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Server responded:", data); // Debugging line

        // 1. Hide the Modal
        document.getElementById('loginModal').classList.add('hidden');
        
        // 2. Hide Page 1 (Landing)
        document.getElementById('page1').classList.remove('active');
        document.getElementById('page1').classList.add('hidden');
        
        // 3. Show Page 2 (Dashboard)
        document.getElementById('page2').classList.remove('hidden');
        document.getElementById('page2').classList.add('active');

        // 4. Update the greeting
        document.getElementById('welcome-msg').innerText = `Director: ${data.username}`;
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Server connection failed. Is 'python app.py' running?");
    });
}

function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(el => el.classList.add('hidden'));
    
    // Show the target section
    const target = document.getElementById(`section-${sectionId}`);
    if (target) target.classList.remove('hidden');

    // Update Sidebar highlighting
    document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
    // Note: detailed sidebar logic allows simplified matching here
    event.target.classList.add('active'); 
}

// --- AI Generation Logic ---

function generateContent() {
    const story = document.getElementById('storyInput').value;
    if (!story) return alert("Please enter a story concept first.");

    const btn = document.getElementById('generateBtn');
    const spinner = document.getElementById('loadingSpinner');
    
    // UI Loading State
    btn.disabled = true;
    btn.innerText = "Generating...";
    spinner.classList.remove('hidden');

    // Call the Backend API
    fetch('/generate_content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storyline: story })
    })
    .then(res => res.json())
    .then(data => {
        // Reset UI
        btn.disabled = false;
        btn.innerText = "Generate Assets";
        spinner.classList.add('hidden');

        // ... inside .then(data => { ...

        if (data.success) {
            // THE PAINTER FUNCTION: Adds color to plain text
            const paintScript = (text) => {
                if (!text) return "";
                return text
                    // Color SCENE HEADINGS (INT/EXT) Gold
                    .replace(/(INT\..*|EXT\..*|FADE IN:|CUT TO:)/g, '<span class="scene-heading">$1</span>')
                    // Color CHARACTER NAMES (Capitalized names) White/Underlined
                    .replace(/([A-Z]{3,}[A-Z\s]*)(?=\n|$)/gm, '<span class="char-name">$1</span>');
            };

            // Use .innerHTML so the spans render as color
            document.getElementById('output-screenplay').innerHTML = paintScript(data.data.screenplay);
            
            // For other sections, we can use simple formatting or the same
            document.getElementById('output-characters').innerHTML = data.data.characters.replace(/\n/g, "<br>");
            document.getElementById('output-sound_design').innerHTML = data.data.sound_design.replace(/\n/g, "<br>");

            // Unlock UI...
             document.getElementById('nav-screenplay').classList.remove('disabled');
             document.getElementById('nav-characters').classList.remove('disabled');
             document.getElementById('nav-sound').classList.remove('disabled');
        } else {
            alert("Error: " + (data.error || "Unknown error occurred"));
        }
    })
    .catch(err => {
        console.error(err);
        btn.disabled = false;
        spinner.classList.add('hidden');
        alert("Failed to connect to the server.");
    });
}
