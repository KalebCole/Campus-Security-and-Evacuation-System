document.addEventListener('DOMContentLoaded', function() {
    // Initialize carousels if they exist on the page
    
    const pendingCarouselElement = document.getElementById('pendingCarousel');
    if (pendingCarouselElement) {
        new bootstrap.Carousel(pendingCarouselElement, {
            interval: false, // Do not automatically cycle
            wrap: true       // Allow wrapping from last to first slide
        });
    }
    
    const todayCarouselElement = document.getElementById('todayCarousel');
    if (todayCarouselElement) {
        new bootstrap.Carousel(todayCarouselElement, {
            interval: false,
            wrap: true
        });
    }

});
