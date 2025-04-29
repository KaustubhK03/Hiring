document.addEventListener('DOMContentLoaded', function() {
    const logoutButton = document.getElementById('logout-button');
    const overlay = document.querySelector('.overlay-modal');
    const closeButton = document.getElementById('close-logout-modal');

    if (logoutButton && overlay && closeButton) {
        logoutButton.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default form submission
            overlay.classList.remove('hide'); // Corrected class name
        });

        closeButton.addEventListener('click', function() {
            overlay.classList.add('hide');
        });

        overlay.addEventListener('click', function(event){
            if (event.target === overlay) {
                overlay.classList.add('hide');
            }
        });
    }
});