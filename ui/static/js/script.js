// Global state
let currentAccounts = [];
let selectedAccount = null;
let showFullAddresses = false;

// DOM Ready - consolidated single listener
document.addEventListener('DOMContentLoaded', function() {
    loadAndDisplayAccounts();
    populateAccountSelectors();
    setupEventListeners();
    showSection('listSelectAccounts');
});

// Setup all event listeners
function setupEventListeners() {
    // Event listeners no longer needed for header dropdown
}

// Section Navigation
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(sectionId).classList.add('active');
    
    // Update account selectors in other sections
    populateAccountSelectors();
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

// Load and display accounts in the list view
async function loadAndDisplayAccounts() {
    try {
        const response = await fetch('/api/accounts');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        currentAccounts = data.accounts || [];
        
        const accountsList = document.getElementById('accountsList');
        
        if (!currentAccounts || currentAccounts.length === 0) {
            accountsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No accounts created yet.</p>
                    <p><small>Create a new account to get started.</small></p>
                </div>
            `;
            updateActiveAccountDisplay();
            return;
        }
        
        let html = '<div class="accounts-grid">';
        currentAccounts.forEach((address) => {
            const shortAddress = address.substring(0, 10) + '...';
            const isSelected = selectedAccount === address ? 'selected' : '';
            html += `
                <div class="account-card ${isSelected}">
                    <div class="account-header">
                        <i class="fas fa-wallet"></i>
                        <span class="account-status ${isSelected ? 'active' : 'inactive'}">
                            ${isSelected ? 'SELECTED' : 'AVAILABLE'}
                        </span>
                    </div>
                    <div class="account-address">
                        <code>${address}</code>
                    </div>
                    <button class="btn-primary" onclick="selectAccountFromList('${address}')">
                        <i class="fas fa-check"></i> Select Account
                    </button>
                </div>
            `;
        });
        html += '</div>';
        
        accountsList.innerHTML = html;
        updateActiveAccountDisplay();
        showToast('Accounts loaded successfully', 'success');
    } catch (error) {
        console.error('Error loading accounts:', error);
        showToast(`Error loading accounts: ${error.message}`, 'error');
        document.getElementById('accountsList').innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>Error loading accounts: ${error.message}</p>
            </div>
        `;
    }
}

// Update the header display with currently selected account
function updateActiveAccountDisplay() {
    const display = document.getElementById('activeAccountDisplay');
    if (selectedAccount) {
        display.innerHTML = `
            <div style="display: flex; align-items: center; gap: 15px; color: white;">
                <div>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">Active Account</p>
                    <code style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px; font-size: 0.85rem;">${selectedAccount}</code>
                </div>
            </div>
        `;
    } else {
        display.innerHTML = '<p style="color: rgba(255,255,255,0.7); margin: 0;">No account selected</p>';
    }
}

// Select account from list
async function selectAccountFromList(address) {
    try {
        const formData = new FormData();
        formData.append('account_id', address);
        
        const response = await fetch('/api/accounts/select', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        selectedAccount = data.current_account;
        
        // Refresh the display
        await loadAndDisplayAccounts();
        showToast(`Selected account: ${selectedAccount.substring(0, 10)}...`, 'success');
    } catch (error) {
        console.error('Error selecting account:', error);
        showToast(`Error selecting account: ${error.message}`, 'error');
    }
}

// Populate all account selectors in forms
function populateAccountSelectors() {
    const accountSelectors = [
        'didAccountId',
        'listAccountId',
        'keysAccountId',
        'claimAccountId'
    ];
    
    accountSelectors.forEach(selectorId => {
        const select = document.getElementById(selectorId);
        if (select) {
            select.innerHTML = '<option value="">Select Account</option>';
            
            if (currentAccounts && currentAccounts.length > 0) {
                currentAccounts.forEach((account) => {
                    const option = document.createElement('option');
                    option.value = account;
                    // Always show full address in form dropdowns
                    option.textContent = account;
                    if (selectedAccount === account) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            }
        }
    });
}

// Create Account
async function createAccount() {
    const resultDiv = document.getElementById('accountResult');
    
    try {
        const response = await fetch('/api/accounts/create', {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <h4><i class="fas fa-check-circle"></i> Account Created Successfully</h4>
                <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>Address:</strong> <code>${data.address}</code></p>
                </div>
            </div>
        `;
        
        showToast('Account created successfully', 'success');
        
        // Reload accounts
        await loadAndDisplayAccounts();
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error creating account: ${error.message}`, 'error');
    }
}

// Import Accounts (if backend supports it - otherwise remove this)
async function importAccounts() {
    const importData = document.getElementById('importData').value.trim();
    const resultDiv = document.getElementById('importResult');
    
    if (!importData) {
        showToast('Please enter import data', 'error');
        return;
    }
    
    try {
        // Validate JSON
        JSON.parse(importData);
        
        const formData = new FormData();
        formData.append('import_data', importData);
        
        const response = await fetch('/api/accounts/import', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <h4><i class="fas fa-check-circle"></i> Accounts Imported Successfully</h4>
                <pre>${JSON.stringify(data, null, 2)}</pre>
            </div>
        `;
        
        showToast('Accounts imported successfully', 'success');
        document.getElementById('importData').value = '';
        await loadAndDisplayAccounts();
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error importing accounts: ${error.message}`, 'error');
    }
}

// Create DID Document
async function createDidDoc() {
    const orgName = document.getElementById('didOrgName').value.trim();
    const namespace = document.getElementById('didNamespace').value.trim() || 'org';
    let entityId = document.getElementById('didEntityId').value.trim();
    if (!entityId) {
        entityId = orgName.toLowerCase().replace(/\s+/g, '-');
    }
    const jurisdiction = document.getElementById('didJurisdiction').value.trim() || 'US';
    const tier = document.getElementById('didTier').value || 'S';
    const accountId = document.getElementById('didAccountId').value;
    const signAfter = document.getElementById('signAfterCreate').checked;
    const registerAfter = document.getElementById('registerAfterCreate').checked;
    const resultDiv = document.getElementById('didDocResult');
    
    if (!orgName || !accountId) {
        showToast('Please fill in organization name and select an account', 'error');
        return;
    }
    
    try {
        // Collect verification methods from form
        const vms = [];
        document.querySelectorAll('#verificationMethods .vm-row').forEach(row => {
            const vmId = row.querySelector('.vm-id').value.trim();
            const vmType = row.querySelector('.vm-type').value;
            const vmController = row.querySelector('.vm-controller').value.trim();
            const vmPublic = row.querySelector('.vm-public').value.trim();
            
            // Only add if public key is provided
            if (vmPublic) {
                vms.push({
                    id: vmId || undefined,
                    type: vmType,
                    controller: vmController || undefined,
                    public_key: vmPublic
                });
            }
        });
        
        // Build form data
        const formData = new FormData();
        formData.append('organization_name', orgName);
        formData.append('namespace', namespace);
        formData.append('entity_identifier', entityId);
        formData.append('jurisdiction', jurisdiction);
        formData.append('tier', tier);
        formData.append('account_id', accountId);
        formData.append('sign_after_create', signAfter ? '1' : '0');
        formData.append('register_after_create', registerAfter ? '1' : '0');
        formData.append('verification_methods', JSON.stringify(vms));
        
        // Make request
        const response = await fetch('/api/diddoc/create', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`HTTP ${response.status}: ${error}`);
        }
        
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <h4><i class="fas fa-check-circle"></i> DID Document Created Successfully</h4>
                <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>DID:</strong> <code>${data.did}</code></p>
                    <p><strong>Organization:</strong> ${orgName}</p>
                    <p><strong>Status:</strong> Created ${data.signed ? '& Signed' : ''} ${data.registered ? '& Registered' : ''}</p>
                </div>
                <pre style="background: #f1f1f1; padding: 10px; border-radius: 5px; overflow-x: auto; max-height: 400px;">
${JSON.stringify(data.diddoc || data, null, 2)}
                </pre>
            </div>
        `;
        
        showToast('DID Document created successfully', 'success');
        
        // Clear form
        document.getElementById('didOrgName').value = '';
        document.getElementById('didEntityId').value = '';
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error creating DID Document: ${error.message}`, 'error');
    }
}

// Load DID Documents
async function loadDidDocs() {
    const accountId = document.getElementById('listAccountId').value;
    const resultDiv = document.getElementById('didDocsList');
    
    if (!accountId) {
        showToast('Please select an account', 'error');
        return;
    }
    
    try {
        // Select account first
        const selectFormData = new FormData();
        selectFormData.append('account_id', accountId);
        
        const selectResponse = await fetch('/api/accounts/select', {
            method: 'POST',
            body: selectFormData
        });
        
        if (!selectResponse.ok) throw new Error('Failed to select account');
        
        // Now list DID docs
        const response = await fetch('/api/diddoc/list');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        if (!data.diddocs || data.diddocs.length === 0) {
            resultDiv.innerHTML = `
                <div class="result-item">
                    <p><i class="fas fa-info-circle"></i> No DID Documents found for this account.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="result-item"><h4><i class="fas fa-list"></i> DID Documents</h4>';
        
        data.diddocs.forEach((doc, index) => {
            html += `
                <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #dee2e6;">
                    <h5>DID: ${doc.id || `Document ${index + 1}`}</h5>
                    <button class="btn-secondary" onclick="signDidDoc(${index})">
                        <i class="fas fa-pen"></i> Sign Document
                    </button>
                    <pre style="background: #f1f1f1; padding: 10px; border-radius: 5px; overflow-x: auto; margin-top: 10px;">
${JSON.stringify(doc, null, 2)}
                    </pre>
                </div>
            `;
        });
        
        html += '</div>';
        resultDiv.innerHTML = html;
        
        showToast('DID Documents loaded successfully', 'success');
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error loading DID Documents: ${error.message}`, 'error');
    }
}

// Sign DID Document
async function signDidDoc(index) {
    const resultDiv = document.getElementById('didDocsList');
    
    try {
        const formData = new FormData();
        formData.append('diddoc_index', index);
        
        const response = await fetch('/api/diddoc/sign', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        showToast('DID Document signed successfully', 'success');
        await loadDidDocs(); // Reload to show updated document
    } catch (error) {
        showToast(`Error signing DID Document: ${error.message}`, 'error');
    }
}

// Show Private Keys
async function showPrivateKeys() {
    const accountId = document.getElementById('keysAccountId').value;
    const resultDiv = document.getElementById('keysResult');
    
    if (!accountId) {
        showToast('Please select an account', 'error');
        return;
    }
    
    try {
        // Select account first
        const selectFormData = new FormData();
        selectFormData.append('account_id', accountId);
        
        const selectResponse = await fetch('/api/accounts/select', {
            method: 'POST',
            body: selectFormData
        });
        
        if (!selectResponse.ok) throw new Error('Failed to select account');
        
        // Export private key
        const response = await fetch('/api/keys/export');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <h4><i class="fas fa-key"></i> Private Keys</h4>
                <div style="background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>⚠️ Warning:</strong> This is a sensitive private key. Handle with care!</p>
                </div>
                <div style="background: #2c3e50; color: #fff; padding: 15px; border-radius: 8px;">
                    <p><strong>Private Key:</strong></p>
                    <code style="word-break: break-all; font-size: 0.85rem;">${data.private_key}</code>
                    <button style="margin-top: 10px; padding: 8px 15px; background: #4FC3F7; border: none; color: white; border-radius: 5px; cursor: pointer;" onclick="copyToClipboard('${data.private_key}')">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
            </div>
        `;
        
        showToast('Private key exported successfully', 'success');
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error exporting private keys: ${error.message}`, 'error');
    }
}

// Load Issuers for selected account
async function loadIssuers() {
    const accountId = document.getElementById('claimAccountId').value;
    const issuerSelect = document.getElementById('claimIssuer');
    
    if (!accountId) {
        issuerSelect.innerHTML = '<option value="">Select Issuer</option>';
        return;
    }
    
    try {
        // For now, use the selected account as issuer (DIDs from that account)
        const selectFormData = new FormData();
        selectFormData.append('account_id', accountId);
        
        const selectResponse = await fetch('/api/accounts/select', {
            method: 'POST',
            body: selectFormData
        });
        
        if (!selectResponse.ok) throw new Error('Failed to select account');
        
        // Load DID docs to use as issuers
        const response = await fetch('/api/account/issuers');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        issuerSelect.innerHTML = '<option value="">Select Issuer</option>';
        
        if (data.issuer && data.issuer.length > 0) {
            data.issuer.forEach(doc => {
                const option = document.createElement('option');
                option.value = doc;
                option.textContent = doc;
                issuerSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading issuers:', error);
        showToast(`Error loading issuers: ${error.message}`, 'error');
    }
}

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

// Create Claim
/*async function createClaim() {
    const accountId = document.getElementById('claimAccountId').value;
    const issuer = document.getElementById('claimIssuer').value;
    const claimType = document.querySelector('input[name="claimType"]:checked').value;
    const resultDiv = document.getElementById('claimResult');
    
    if (!accountId || !issuer) {
        showToast('Please select account and issuer', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('issuer', issuer);
        
        if (claimType === 'message') {
            const message = document.getElementById('claimMessage').value.trim();
            if (!message) {
                showToast('Please enter a message', 'error');
                return;
            }
            formData.append('message', message);
        } else {
            const fileInput = document.getElementById('claimFile');
            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Please select a file', 'error');
                return;
            }
            formData.append('file', fileInput.files[0]);
        }
        
        const response = await fetch('/api/claims/create', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="result-item">
                <h4><i class="fas fa-check-circle"></i> Claim Created Successfully</h4>
                <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>Claim ID:</strong> <code>${data.claim_id}</code></p>
                    <p><strong>Issuer:</strong> ${issuer}</p>
                    <p><strong>Status:</strong> Created & Signed</p>
                </div>
                <pre style="background: #f1f1f1; padding: 10px; border-radius: 5px; overflow-x: auto;">
${JSON.stringify(data.claim, null, 2)}
                </pre>
            </div>
        `;
        
        showToast('Claim created and signed successfully', 'success');
        
        // Clear form
        document.getElementById('claimMessage').value = '';
        document.getElementById('claimFile').value = '';
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="result-item" style="border-left-color: #f44336;">
                <h4><i class="fas fa-exclamation-circle"></i> Error</h4>
                <p>${error.message}</p>
            </div>
        `;
        showToast(`Error creating claim: ${error.message}`, 'error');
    }
}*/

// Utility function to copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

// Add/remove verification method UI helpers
function addVM() {
  const container = document.getElementById('verificationMethods');
  const row = document.createElement('div');
  row.className = 'vm-row';
  row.innerHTML = `
    <input class="vm-id" placeholder="id (optional)">
    <select class="vm-type">
      <option>Ed25519VerificationKey2020</option>
      <option>Ed25519VerificationKey2018</option>
      <option>JsonWebKey2020</option>
    </select>
    <input class="vm-controller" placeholder="controller (defaults to did)">
    <input class="vm-public" placeholder="public key / address">
    <button type="button" onclick="removeVM(this)">Remove</button>
  `;
  container.appendChild(row);
}
function removeVM(btn) { btn.parentElement.remove(); }

// Update account dropdown to show full or trimmed addresses
function updateAccountDropdown() {
  const select = document.getElementById('didAccountId');
  if (!select) return;
  select.innerHTML = '<option value="">Select Account</option>';
  (currentAccounts || []).forEach(addr => {
    const opt = document.createElement('option');
    opt.value = addr;
    opt.textContent = showFullAddresses ? addr : `${addr.substring(0,10)}...`;
    select.appendChild(opt);
  });
}

// Create DID doc with additional fields and VMs
async function createDidDoc() {
  const org = document.getElementById('didOrgName').value.trim();
  const ns = document.getElementById('didNamespace').value.trim() || 'org';
  let entity = document.getElementById('didEntityId').value.trim();
  if (!entity) entity = org.toLowerCase().replace(/\s+/g, '-');
  const jurisdiction = document.getElementById('didJurisdiction').value || 'US';
  const tier = document.getElementById('didTier').value || 'S';
  const account = document.getElementById('didAccountId').value;
  const signAfter = document.getElementById('signAfterCreate').checked;
  const registerAfter = document.getElementById('registerAfterCreate').checked;

  if (!org || !account) { showToast('Organization and account required','error'); return; }

  // Collect verification methods from UI
  const vms = [];
  document.querySelectorAll('#verificationMethods .vm-row').forEach(row => {
    const id = row.querySelector('.vm-id').value.trim();
    const type = row.querySelector('.vm-type').value;
    const controller = row.querySelector('.vm-controller').value.trim();
    const pub = row.querySelector('.vm-public').value.trim();
    if (pub) {
      vms.push({
        id: id || undefined,
        type,
        controller: controller || undefined,
        public_key: pub
      });
    }
  });

  const form = new FormData();
  form.append('organization_name', org);
  form.append('namespace', ns);
  form.append('entity_identifier', entity);
  form.append('jurisdiction', jurisdiction);
  form.append('tier', tier);
  form.append('account_id', account);
  form.append('sign_after_create', signAfter ? '1' : '0');
  form.append('register_after_create', registerAfter ? '1' : '0');
  form.append('verification_methods', JSON.stringify(vms));

  try {
    const res = await fetch('/api/diddoc/create', { method: 'POST', body: form });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    document.getElementById('didDocResult').innerText = JSON.stringify(data, null, 2);
    showToast('DID Document created', 'success');

    // if backend returned actions performed, show them
    // reload DID docs list
    await loadDidDocs();
  } catch (err) {
    showToast('Error creating DIDDOC: ' + err.message, 'error');
    document.getElementById('didDocResult').innerText = err.message;
  }
}

// Create claim extended: allow sign + register flags
async function createClaim() {
  const accountId = document.getElementById('claimAccountId').value;
  const issuer = document.getElementById('claimIssuer').value;
  const claimType = document.querySelector('input[name="claimType"]:checked').value;
  const signAfter = document.getElementById('claimSignAfter').checked;
  const registerAfter = document.getElementById('claimRegisterAfter').checked;

  if (!accountId || !issuer) { showToast('Account and issuer required','error'); return; }

  const form = new FormData();
  form.append('issuer', issuer);
  form.append('sign_after_create', signAfter ? '1' : '0');
  form.append('register_after_create', registerAfter ? '1' : '0');

  if (claimType === 'message') {
    const message = document.getElementById('claimMessage').value.trim();
    if (!message) { showToast('Message required','error'); return; }
    form.append('message', message);
  } else {
    const file = document.getElementById('claimFile').files[0];
    if (!file) { showToast('File required','error'); return; }
    form.append('file', file);
  }

  // ensure account selected on backend
  const selForm = new FormData();
  selForm.append('account_id', accountId);
  await fetch('/api/accounts/select', { method: 'POST', body: selForm });

  try {
    const res = await fetch('/api/claims/create', { method: 'POST', body: form });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    document.getElementById('claimResult').innerText = JSON.stringify(data, null, 2);
    showToast('Claim created', 'success');
  } catch (err) {
    showToast('Error creating claim: ' + err.message, 'error');
  }
}
