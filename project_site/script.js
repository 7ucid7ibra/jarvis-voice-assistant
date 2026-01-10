document.addEventListener('DOMContentLoaded', () => {

    // --- Optimized Parallax (RequestAnimationFrame) ---
    const heroSection = document.querySelector('.hero');
    let ticking = false;

    if (heroSection) {
        heroSection.addEventListener('mousemove', (e) => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const x = (window.innerWidth / 2 - e.pageX) / 50; // Increased divider for subtler effect
                    const y = (window.innerHeight / 2 - e.pageY) / 50;

                    // Only select elements if they exist
                    const rings = document.querySelectorAll('.rotating-ring');
                    if (rings.length) {
                        rings.forEach((ring, index) => {
                            const speed = (index + 1) * 0.3;
                            ring.style.transform = `translate(calc(-50% + ${x * speed}px), calc(-50% + ${y * speed}px))`;
                        });
                    }
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    // --- Tooltip Logic (Improved for Mobile & Interaction) ---
    const terms = document.querySelectorAll('.tech-term');
    const tooltipPopup = document.createElement('div');
    tooltipPopup.className = 'tooltip-popup';
    document.body.appendChild(tooltipPopup);

    function showTooltip(term) {
        const desc = term.getAttribute('data-tooltip') || term.getAttribute('data-desc');
        tooltipPopup.textContent = desc;
        tooltipPopup.classList.add('show');

        // Position it
        const rect = term.getBoundingClientRect();
        const popupRect = tooltipPopup.getBoundingClientRect();

        let top = rect.top - popupRect.height - 10 + window.scrollY;
        let left = rect.left + (rect.width / 2) - (popupRect.width / 2) + window.scrollX;

        // Prevent tooltip from going off-screen (left/right)
        if (left < 10) left = 10;
        if (left + popupRect.width > window.innerWidth - 10) {
            left = window.innerWidth - popupRect.width - 10;
        }

        tooltipPopup.style.top = `${top}px`;
        tooltipPopup.style.left = `${left}px`;
    }

    function hideTooltip() {
        tooltipPopup.classList.remove('show');
    }

    terms.forEach(term => {
        // Desktop - only show on hover if it's NOT a touch interaction recently
        term.addEventListener('mouseenter', () => {
            if (window.matchMedia("(hover: hover)").matches) {
                showTooltip(term);
            }
        });

        term.addEventListener('mouseleave', () => {
            if (window.matchMedia("(hover: hover)").matches) {
                hideTooltip();
            }
        });

        // Click for both (but handles mobile toggle cleanly)
        term.addEventListener('click', (e) => {
            e.stopPropagation();

            // If we are on mobile (no hover) or it was a tap
            if (!window.matchMedia("(hover: hover)").matches || e.pointerType === 'touch') {
                if (tooltipPopup.classList.contains('show')) {
                    hideTooltip();
                } else {
                    showTooltip(term);
                }
            }
        });
    });

    // Hide tooltip when clicking anywhere else
    document.addEventListener('click', (e) => {
        if (!e.target.classList.contains('tech-term')) {
            hideTooltip();
        }
    });


    // Mobile Menu Toggle
    const mobileBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');

    if (mobileBtn && navLinks) {
        mobileBtn.addEventListener('click', () => {
            mobileBtn.classList.toggle('active');
            navLinks.classList.toggle('active');
        });

        // Close menu when clicking a link
        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', () => {
                mobileBtn.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });
    }

    // Universal Expandable Cards (Tiles)
    const expandableCards = document.querySelectorAll('.flow-step, .model-card, .deep-dive');
    const modelCards = document.querySelectorAll('.model-card');

    expandableCards.forEach(card => {
        card.addEventListener('click', () => {
            const isModelCard = card.classList.contains('model-card');
            const isDesktop = window.innerWidth > 968;

            if (isModelCard && isDesktop) {
                // Synchronized behavior for model cards on desktop
                const isGroupActive = card.classList.contains('active');
                modelCards.forEach(mCard => {
                    if (isGroupActive) {
                        mCard.classList.remove('active');
                    } else {
                        mCard.classList.add('active');
                    }
                });
            } else {
                // Independent behavior for flow-steps or mobile model cards
                card.classList.toggle('active');
            }
        });
    });

    // --- Philosophy Gallery Controller ---
    const phiGallery = document.querySelector('.phi-gallery-container');
    if (phiGallery) {
        const track = phiGallery.querySelector('.phi-track');
        const slides = Array.from(phiGallery.querySelectorAll('.phi-slide'));
        const nextBtn = phiGallery.querySelector('.phi-nav.next');
        const prevBtn = phiGallery.querySelector('.phi-nav.prev');
        const dots = Array.from(phiGallery.querySelectorAll('.phi-dots .dot'));

        let currentIndex = 0;
        let isMoving = false;

        function updateGallery(index) {
            if (isMoving) return;
            isMoving = true;

            currentIndex = index;

            // Move track
            track.style.transform = `translateX(-${currentIndex * 100}%)`;

            // Update active states
            slides.forEach((slide, i) => {
                slide.classList.toggle('active', i === currentIndex);
            });

            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === currentIndex);
            });

            // Unlock after transition
            setTimeout(() => { isMoving = false; }, 500);
        }

        // Auto-play logic with reset
        let autoPlayInterval;

        function startAutoPlay() {
            if (window.innerWidth <= 768) return; // Disable auto-play on mobile

            autoPlayInterval = setInterval(() => {
                let nextIndex = (currentIndex + 1) % slides.length;
                updateGallery(nextIndex);
            }, 5000); // 5 seconds per slide
        }

        function resetAutoPlay() {
            clearInterval(autoPlayInterval);
            startAutoPlay();
        }

        nextBtn.addEventListener('click', () => {
            let nextIndex = (currentIndex + 1) % slides.length;
            updateGallery(nextIndex);
            resetAutoPlay();
        });

        prevBtn.addEventListener('click', () => {
            let prevIndex = (currentIndex - 1 + slides.length) % slides.length;
            updateGallery(prevIndex);
            resetAutoPlay();
        });

        dots.forEach((dot, i) => {
            dot.addEventListener('click', () => {
                updateGallery(i);
                resetAutoPlay();
            });
        });

        // Initialize auto-play
        startAutoPlay();

        // Pause auto-play on interaction
        phiGallery.addEventListener('mouseenter', () => clearInterval(autoPlayInterval));
        phiGallery.addEventListener('mouseleave', () => startAutoPlay());

        // --- Swipe Support ---
        let touchStartX = 0;
        let touchEndX = 0;

        phiGallery.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            clearInterval(autoPlayInterval); // Pause auto-play while touching
        }, { passive: true });

        phiGallery.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
            startAutoPlay(); // Resume auto-play after swipe
        }, { passive: true });

        function handleSwipe() {
            const swipeDistance = touchStartX - touchEndX;
            const threshold = 50; // Minimum distance for a swipe

            if (Math.abs(swipeDistance) > threshold) {
                if (swipeDistance > 0) {
                    // Swiped left -> Next slide
                    let nextIndex = (currentIndex + 1) % slides.length;
                    updateGallery(nextIndex);
                } else {
                    // Swiped right -> Previous slide
                    let prevIndex = (currentIndex - 1 + slides.length) % slides.length;
                    updateGallery(prevIndex);
                }
                resetAutoPlay();
            }
        }
    }

    console.log('⚡ Jarvis Smart Home: Navigation ready');
});
