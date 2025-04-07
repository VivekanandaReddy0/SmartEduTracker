document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const htmlElement = document.documentElement;
    
    // Check localStorage for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    // Apply saved theme if exists, otherwise default to light
    if (savedTheme === 'dark') {
        htmlElement.setAttribute('data-bs-theme', 'dark');
        darkModeToggle.checked = true;
    } else {
        htmlElement.setAttribute('data-bs-theme', 'light');
        darkModeToggle.checked = false;
    }
    
    // Toggle theme when switch is clicked
    darkModeToggle.addEventListener('change', function() {
        if (this.checked) {
            // Switch to dark mode
            htmlElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            // Switch to light mode
            htmlElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
});
