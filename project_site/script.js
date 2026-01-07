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

    // --- Tooltip Logic (Restored) ---
    const terms = document.querySelectorAll('.tech-term');
    const tooltipPopup = document.createElement('div');
    tooltipPopup.className = 'tooltip-popup';
    document.body.appendChild(tooltipPopup);

    terms.forEach(term => {
        term.addEventListener('mouseenter', () => {
            const desc = term.getAttribute('data-desc');
            tooltipPopup.textContent = desc;
            tooltipPopup.classList.add('show');

            const rect = term.getBoundingClientRect();
            const popupRect = tooltipPopup.getBoundingClientRect();

            // Position above the term
            let top = rect.top - popupRect.height - 10 + window.scrollY;
            let left = rect.left + (rect.width / 2) - (popupRect.width / 2) + window.scrollX;

            tooltipPopup.style.top = `${top}px`;
            tooltipPopup.style.left = `${left}px`;
        });

        term.addEventListener('mouseleave', () => {
            tooltipPopup.classList.remove('show');
        });
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

    // Interactive Flow Steps (Expandable Tiles)
    const flowSteps = document.querySelectorAll('.flow-step');
    flowSteps.forEach(step => {
        step.addEventListener('click', () => {
            // Check if this step is already active
            const isActive = step.classList.contains('active');

            // Close all steps first (optional: uncomment if you want accordian style)
            // flowSteps.forEach(s => s.classList.remove('active'));

            // Toggle this step
            if (isActive) {
                step.classList.remove('active');
            } else {
                step.classList.add('active');
            }
        });
    });

    console.log('⚡ Jarvis Smart Home: Navigation ready');
});
