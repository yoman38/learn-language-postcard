document.querySelectorAll('.level').forEach(level => {
    level.addEventListener('click', function() {
        let selectedLevel = this.innerText;

        // Hide all feature cards
        document.querySelectorAll('.feature-card').forEach(card => {
            card.style.display = 'none';
        });

        // Show feature cards matching selected level
        document.querySelectorAll(`.feature-card[data-level*="${selectedLevel}"]`).forEach(card => {
            card.style.display = 'block';
        });
    });
});
