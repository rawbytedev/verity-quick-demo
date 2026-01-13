async function verifyClaim() {
    const input = document.getElementById('claimUrl').value.trim();
    const loading = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const claimType = document.querySelector('input[name="claimType"]:checked').value;
    const form = new FormData();
    if (claimType === 'message') {
        const message = document.getElementById('claimMessage').value.trim();
        if (!message) {
            showToast('Message required', 'error');
            return;
        }
        form.append('message', message);
    } else {
        const file = document.getElementById('claimFile').files[0];
        if (!file) {
            showToast('File required', 'error');
            return;
        }
        form.append('file', file);
    }
    if (!input) {
        showToast('Please enter a verification URL or Claim ID', "error");
        return;
    }
    

    // Extract claim ID from URL if needed
    let claimId = input;
    if (input.includes('/verify/')) {
        claimId = input.split('/verify/').pop();
    } else if (input.includes('cid=')) {
        claimId = new URL(input).searchParams.get('cid');
    }
    form.append("claim_id", claimId)

    loading.style.display = 'block';
    resultDiv.style.display = 'none';

    try {
        let response;
        response = await fetch(`/verify/post/claim`, 
            {method:'POST',
            body:form}
        );
        const data = await response.json();

        // Display results
        resultDiv.innerHTML = '';
        resultDiv.className = 'result ' + (data.verified ? 'verified' : 'not-verified');

        const badge = data.verified
            ? '<div class="badge">✅ VERIFIED & VALID</div>'
            : '<div class="badge">❌ NOT VERIFIED</div>';

        const issuer = data.issuer_name || data.issuer?.did || 'Unknown';
        const tier = data.verification_tier ? `Tier ${data.verification_tier}` : 'Unknown Tier';

        let stepsHtml = '<h3>Verification Steps:</h3>';
        for (const [step, success] of Object.entries(data.steps || {})) {
            const stepName = step.replace('_', ' ').replace(/\b\\w/g, l => l.toUpperCase());
            stepsHtml += `<div class="step ${success ? 'success' : 'failure'}">${success ? '✓' : '✗'} ${stepName}</div>`;
        }

        resultDiv.innerHTML = `
                        ${badge}
                        <h2>${issuer}</h2>
                        <p><strong>Status:</strong> ${data.verified ? 'Cryptographically verified' : 'Verification failed'}</p>
                        <p><strong>Claim ID:</strong> ${data.claim_id}</p>
                        <p><strong>Verification Tier:</strong> ${tier}</p>
                        <p><strong>Time:</strong> ${new Date(data.verification_time).toLocaleString()}</p>
                        ${data.error_message ? `<p><strong>Error:</strong> ${data.error_message}</p>` : ''}
                        ${stepsHtml}
                        ${data.verified ? '<p style="margin-top: 20px; font-size: 18px; color: #155724;">This content is authentic and has not been tampered with.</p>' : ''}
                    `;

    } catch (error) {
        resultDiv.className = 'result not-verified';
        resultDiv.innerHTML = `
                        <div class="badge">❌ VERIFICATION ERROR</div>
                        <p>Unable to verify claim: ${error.message}</p>
                    `;
    } finally {
        loading.style.display = 'none';
        resultDiv.style.display = 'block';
    }
}
// Allow Enter key to trigger verification
document.getElementById('claimUrl').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') verifyClaim();
});

// Toggle between message and file input
function toggleClaimInput() {
    const messageInput = document.getElementById('messageInput');
    const fileInput = document.getElementById('fileInput');
    const claimType = document.querySelector('input[name="claimType"]:checked').value;

    if (claimType === 'message') {
        messageInput.style.display = 'block';
        fileInput.style.display = 'none';
    } else {
        messageInput.style.display = 'none';
        fileInput.style.display = 'block';
    }
}
// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show ' + type;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}