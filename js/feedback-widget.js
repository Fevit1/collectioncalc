/**
 * Floating Feedback Widget
 * Shows a "Feedback" pill on all user-facing pages.
 * Opens a modal with 5-star rating + textarea.
 * Posts to /api/feedback/general.
 * Only shown when user is logged in.
 */
(function() {
    'use strict';

    // Only show for logged-in users
    const token = localStorage.getItem('cc_token');
    if (!token) return;

    // Don't show on admin page
    if (window.location.pathname.includes('admin')) return;

    // API URL — use global if available, otherwise default
    const apiUrl = (typeof API_URL !== 'undefined') ? API_URL : 'https://collectioncalc-docker.onrender.com';

    // Inject CSS
    const style = document.createElement('style');
    style.textContent = `
        .fw-trigger {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #fff;
            border: none;
            border-radius: 24px;
            padding: 10px 18px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
            z-index: 9998;
            transition: transform 0.2s, box-shadow 0.2s;
            font-family: inherit;
        }
        .fw-trigger:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }
        .fw-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.6);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }
        .fw-overlay.active { display: flex; }
        .fw-modal {
            background: #1a1a2e;
            border: 1px solid #2d2d44;
            border-radius: 16px;
            padding: 28px;
            width: 90%;
            max-width: 400px;
            color: #e4e4e7;
            position: relative;
        }
        .fw-modal h3 {
            margin: 0 0 4px 0;
            font-size: 1.1rem;
            color: #fff;
        }
        .fw-modal .fw-subtitle {
            color: #71717a;
            font-size: 0.8rem;
            margin-bottom: 1.25rem;
        }
        .fw-close {
            position: absolute;
            top: 12px;
            right: 16px;
            background: none;
            border: none;
            color: #71717a;
            font-size: 1.3rem;
            cursor: pointer;
            padding: 4px;
        }
        .fw-close:hover { color: #fff; }
        .fw-stars {
            display: flex;
            gap: 8px;
            margin-bottom: 1rem;
        }
        .fw-star {
            background: none;
            border: none;
            font-size: 1.8rem;
            cursor: pointer;
            padding: 2px;
            transition: transform 0.15s;
            filter: grayscale(1) opacity(0.4);
        }
        .fw-star.active {
            filter: none;
            transform: scale(1.15);
        }
        .fw-star:hover { transform: scale(1.2); }
        .fw-textarea {
            width: 100%;
            min-height: 80px;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #2d2d44;
            background: #0f0f23;
            color: #e4e4e7;
            resize: vertical;
            font-family: inherit;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        .fw-textarea::placeholder { color: #52525b; }
        .fw-textarea:focus { outline: none; border-color: #6366f1; }
        .fw-submit {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #fff;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: opacity 0.2s;
            font-family: inherit;
        }
        .fw-submit:hover { opacity: 0.9; }
        .fw-submit:disabled { opacity: 0.5; cursor: not-allowed; }
        .fw-success {
            text-align: center;
            padding: 2rem 0;
        }
        .fw-success-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
        .fw-success-text { color: #10b981; font-weight: 600; font-size: 1rem; }
    `;
    document.head.appendChild(style);

    // Create trigger button
    const trigger = document.createElement('button');
    trigger.className = 'fw-trigger';
    trigger.innerHTML = '\uD83D\uDCAC Feedback';
    trigger.setAttribute('aria-label', 'Send feedback');
    document.body.appendChild(trigger);

    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'fw-overlay';
    overlay.innerHTML = `
        <div class="fw-modal">
            <button class="fw-close" aria-label="Close">&times;</button>
            <h3>Share Your Feedback</h3>
            <div class="fw-subtitle">Help us improve Slab Worthy</div>
            <div class="fw-stars" id="fwStars">
                <button class="fw-star" data-rating="1">&#11088;</button>
                <button class="fw-star" data-rating="2">&#11088;</button>
                <button class="fw-star" data-rating="3">&#11088;</button>
                <button class="fw-star" data-rating="4">&#11088;</button>
                <button class="fw-star" data-rating="5">&#11088;</button>
            </div>
            <textarea class="fw-textarea" id="fwComment" placeholder="Tell us what you think..."></textarea>
            <button class="fw-submit" id="fwSubmit" disabled>Submit Feedback</button>
        </div>
    `;
    document.body.appendChild(overlay);

    let selectedRating = 0;

    // Star click handling
    const stars = overlay.querySelectorAll('.fw-star');
    stars.forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.rating);
            stars.forEach(s => {
                s.classList.toggle('active', parseInt(s.dataset.rating) <= selectedRating);
            });
            checkSubmitEnabled();
        });
    });

    // Enable submit when both rating and comment are provided
    const commentInput = overlay.querySelector('#fwComment');
    const submitBtn = overlay.querySelector('#fwSubmit');

    function checkSubmitEnabled() {
        submitBtn.disabled = !(selectedRating > 0 && commentInput.value.trim().length > 0);
    }
    commentInput.addEventListener('input', checkSubmitEnabled);

    // Open modal
    trigger.addEventListener('click', () => {
        overlay.classList.add('active');
    });

    // Close modal
    overlay.querySelector('.fw-close').addEventListener('click', () => {
        overlay.classList.remove('active');
    });
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('active');
    });

    // Submit feedback
    submitBtn.addEventListener('click', async () => {
        if (selectedRating === 0 || !commentInput.value.trim()) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        try {
            const res = await fetch(`${apiUrl}/api/feedback/general`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    rating: selectedRating,
                    comment: commentInput.value.trim(),
                    page_url: window.location.pathname
                })
            });

            const data = await res.json();

            // Show success state
            const modal = overlay.querySelector('.fw-modal');
            modal.innerHTML = `
                <div class="fw-success">
                    <div class="fw-success-icon">&#10003;</div>
                    <div class="fw-success-text">Thanks for your feedback!</div>
                </div>
            `;

            // Close after 2s
            setTimeout(() => {
                overlay.classList.remove('active');
                // Reset modal for next use
                setTimeout(() => {
                    location.reload(); // Simple reset — widget re-initializes
                }, 300);
            }, 2000);

        } catch (e) {
            console.error('Feedback submit error:', e);
            submitBtn.textContent = 'Error — try again';
            submitBtn.disabled = false;
        }
    });
})();
