document.addEventListener('DOMContentLoaded', () => {
    
    // --- Scroll Animations ---
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px"
    };

    const animateOnScroll = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    const elementsToAnimate = document.querySelectorAll('.flow-step, .ui-component, .model-card, .arch-component, .hero-content');
    elementsToAnimate.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        if (el.classList.contains('flow-step') || el.classList.contains('ui-component')) {
            el.style.transitionDelay = `${index * 0.1}s`;
        }
        animateOnScroll.observe(el);
    });

    const style = document.createElement('style');
    style.innerHTML = `
        .visible { opacity: 1 !important; transform: translateY(0) !important; }
    `;
    document.head.appendChild(style);

    // --- Neural Core Parallax ---
    const heroSection = document.querySelector('.hero');
    const neuralCore = document.querySelector('.neural-core');
    
    if (heroSection && neuralCore) {
        heroSection.addEventListener('mousemove', (e) => {
            const x = (window.innerWidth / 2 - e.pageX) / 40;
            const y = (window.innerHeight / 2 - e.pageY) / 40;
            
            const rings = document.querySelectorAll('.rotating-ring');
            rings.forEach((ring, index) => {
                const speed = (index + 1) * 0.5;
                ring.style.transform = `translate(calc(-50% + ${x * speed}px), calc(-50% + ${y * speed}px)) rotate(${Date.now() / (100 + index * 50)}deg)`;
            });

            const waves = document.querySelectorAll('.pulse-wave');
            waves.forEach((wave, index) => {
                const delay = index * 0.5;
                wave.style.animationDelay = `${delay}s`;
            });
        });

        heroSection.addEventListener('mouseleave', () => {
            const rings = document.querySelectorAll('.rotating-ring');
            rings.forEach(ring => {
                ring.style.transform = 'translate(-50%, -50%)';
            });
        });
    }

    // --- Tooltip Logic ---
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

            let top = rect.top - popupRect.height - 10 + window.scrollY;
            let left = rect.left + (rect.width / 2) - (popupRect.width / 2) + window.scrollX;

            tooltipPopup.style.top = `${top}px`;
            tooltipPopup.style.left = `${left}px`;
        });

        term.addEventListener('mouseleave', () => {
            tooltipPopup.classList.remove('show');
        });
    });

    // --- Model Selection Highlighting ---
    const localRadio = document.querySelector('.nav-links a[href="#models"]');
    const modelCards = document.querySelectorAll('.model-card');
    const localModel = document.getElementById('local-model');
    const cloudModel = document.getElementById('cloud-model');

    if (modelCards.length > 0) {
        modelCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-8px) scale(1.02)';
                card.style.borderColor = 'var(--plasma-cyan)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
                card.style.borderColor = '';
            });
        });
    }

    // --- Flow Diagram Interactivity ---
    const steps = document.querySelectorAll('.flow-step');

    steps.forEach(step => {
        step.addEventListener('mouseenter', () => {
            step.style.borderColor = 'var(--plasma-cyan)';
            step.style.boxShadow = '0 15px 35px rgba(55, 230, 255, 0.2)';
        });

        step.addEventListener('mouseleave', () => {
            step.style.borderColor = '';
            step.style.boxShadow = '';
        });
    });

    // --- UI Component Interactivity ---
    const uiComponents = document.querySelectorAll('.ui-component');

    uiComponents.forEach(comp => {
        comp.addEventListener('mouseenter', () => {
            comp.style.transform = 'translateY(-8px)';
            comp.style.borderColor = 'var(--plasma-cyan)';
            comp.style.boxShadow = '0 20px 40px rgba(55, 230, 255, 0.2)';
        });

        comp.addEventListener('mouseleave', () => {
            comp.style.transform = '';
            comp.style.borderColor = '';
            comp.style.boxShadow = '';
        });
    });

    // --- Management Feature Interactivity ---
    const mgmtFeatures = document.querySelectorAll('.mgmt-feature');

    mgmtFeatures.forEach(feature => {
        feature.addEventListener('mouseenter', () => {
            feature.style.background = 'rgba(55, 230, 255, 0.08)';
            feature.style.borderColor = 'var(--plasma-cyan)';
        });

        feature.addEventListener('mouseleave', () => {
            feature.style.background = '';
            feature.style.borderColor = '';
        });
    });

    // --- Smooth Scrolling for Navigation ---
    const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                const offset = 80; // Account for sticky nav
                const targetPosition = targetSection.getBoundingClientRect().top + window.pageYOffset - offset;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // --- Neural Core Glow Enhancement ---
    const reactorCenter = document.querySelector('.reactor-center');
    
    if (reactorCenter) {
        let glowIntensity = 0;
        
        setInterval(() => {
            glowIntensity = Math.abs(Math.sin(Date.now() / 1000));
            reactorCenter.style.boxShadow = `0 0 ${60 + glowIntensity * 20}px var(--electric-blue)`;
        }, 50);
    }

    // --- Particle Enhancement ---
    const particles = document.querySelector('.particles');
    
    if (particles) {
        let particlePositions = [];
        
        for (let i = 0; i < 20; i++) {
            particlePositions.push({
                x: Math.random() * 100,
                y: Math.random() * 100,
                speed: 0.5 + Math.random() * 1.5
            });
        }
        
        setInterval(() => {
            let backgroundValue = '';
            
            particlePositions.forEach((pos, index) => {
                pos.y -= pos.speed;
                
                if (pos.y < 0) {
                    pos.y = 100;
                    pos.x = Math.random() * 100;
                }
                
                const color = index % 2 === 0 ? 'rgba(55, 230, 255, 0.2)' : 'rgba(14, 165, 233, 0.15)';
                backgroundValue += `radial-gradient(2px 2px at ${pos.x}vw ${pos.y}vh, ${color}, transparent), `;
            });
            
            particles.style.backgroundImage = backgroundValue.slice(0, -2);
        }, 50);
    }

    // --- Architecture Component Hover Effects ---
    const archComponents = document.querySelectorAll('.arch-component');

    archComponents.forEach(comp => {
        comp.addEventListener('mouseenter', () => {
            comp.style.borderColor = 'var(--electric-blue)';
            comp.style.transform = 'translateY(-4px)';
            comp.style.boxShadow = '0 15px 30px rgba(14, 165, 233, 0.15)';
        });

        comp.addEventListener('mouseleave', () => {
            comp.style.borderColor = '';
            comp.style.transform = '';
            comp.style.boxShadow = '';
        });
    });

    // --- Feature List Interactivity ---
    const featureItems = document.querySelectorAll('.feature-item');

    featureItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.background = 'rgba(55, 230, 255, 0.08)';
            item.style.borderColor = 'rgba(55, 230, 255, 0.2)';
        });

        item.addEventListener('mouseleave', () => {
            item.style.background = '';
            item.style.borderColor = '';
        });
    });

    // --- Code Window Hover Effect ---
    const codeWindows = document.querySelectorAll('.code-window');

    codeWindows.forEach(win => {
        win.addEventListener('mouseenter', () => {
            win.style.transform = 'scale(1.02)';
            win.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.6)';
            win.style.borderColor = 'var(--plasma-cyan)';
        });

        win.addEventListener('mouseleave', () => {
            win.style.transform = '';
            win.style.boxShadow = '';
            win.style.borderColor = '';
        });
    });

    // --- Status Indicator Enhancement ---
    const statusIndicator = document.querySelector('.status-indicator');
    
    if (statusIndicator) {
        let pulsePhase = 0;
        
        setInterval(() => {
            pulsePhase += 0.1;
            const scale = 1 + Math.sin(pulsePhase) * 0.1;
            const opacity = 0.7 + Math.sin(pulsePhase) * 0.3;
            
            statusIndicator.style.transform = `scale(${scale})`;
            statusIndicator.style.opacity = opacity;
        }, 100);
    }

    // --- Nav Link Active State ---
    const sections = document.querySelectorAll('section[id]');
    const navLinks2 = document.querySelectorAll('.nav-links a[href^="#"]');

    window.addEventListener('scroll', () => {
        const scrollPos = window.scrollY + 100;
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');
            
            if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {
                navLinks2.forEach(link => {
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.style.color = 'var(--plasma-cyan)';
                    } else {
                        link.style.color = 'var(--text-secondary)';
                    }
                });
            }
        });
    });

    console.log('🤖 Jarvis Neural Interface Initialized');
    console.log('🎨 BioMech UI Framework Active');
    console.log('⚡ Reactive Animations Running');
});