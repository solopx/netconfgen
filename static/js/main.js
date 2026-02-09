// Main JavaScript functionality for the Network Configuration Generator

document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        if (alert.classList.contains('alert-success')) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });

    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // IP address validation helper
    window.validateIP = function(ip) {
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipRegex.test(ip);
    };

    // VLAN ID validation helper
    window.validateVLAN = function(vlanId) {
    if (vlanId.toLowerCase() === 'all') return true;
    
    // Se contiver hífen (range) ou vírgula (lista)
    if (vlanId.includes('-') || vlanId.includes(',')) {
        // Validação simples de regex para permitir números, hífens e vírgulas
        return /^[\d\s\-,]+$/.test(vlanId);
    }

    const vlan = parseInt(vlanId);
    return !isNaN(vlan) && vlan >= 1 && vlan <= 4094;
    };

    // Real-time validation for IP address fields
    const ipInputs = document.querySelectorAll('input[name="ip_address"], input[name="gateway"]');
    ipInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value && !validateIP(this.value)) {
                this.setCustomValidity('Please enter a valid IP address');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                if (this.value) this.classList.add('is-valid');
            }
        });
    });

    // Real-time validation for VLAN ID fields
    const vlanInputs = document.querySelectorAll('input[name="vlan_id"], input[name="access_vlan"], input[name="voice_vlan"]');
    vlanInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value && !validateVLAN(this.value)) {
                this.setCustomValidity('Please enter a valid VLAN ID (1-4094)');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                if (this.value) this.classList.add('is-valid');
            }
        });
    });

    const deleteLinks = document.querySelectorAll('a[href*="/delete_"]');
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                event.preventDefault();
            }
        });
    });
});

// Configuration preview functionality
function previewConfig(platform) {
    
    const modal = new bootstrap.Modal(document.getElementById('configPreviewModal'));
    const content = document.getElementById('configPreviewContent');
    content.textContent = 'Loading configuration...';
    modal.show();

    fetch(`/preview_config/${platform}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                content.textContent = `Error: ${data.error}`;
                content.className = 'bg-danger text-light p-3 rounded';
            } else {
                content.textContent = data.config;
                content.className = 'bg-dark text-light p-3 rounded';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            content.textContent = `Error loading configuration preview: ${error.message}`;
            content.className = 'bg-danger text-light p-3 rounded';
        });
}

// Utility function to copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        const toast = document.createElement('div');
        toast.className = 'toast-container position-fixed top-0 end-0 p-3';
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <strong class="me-auto">Success</strong>
                </div>
                <div class="toast-body">
                    Configuration copied to clipboard!
                </div>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}
document.addEventListener('DOMContentLoaded', function() {
    const modeSelect = document.getElementById('mode');
    const accessFields = document.getElementById('access_fields');
    const trunkFields = document.getElementById('trunk_fields');
    const isAosCxCheckbox = document.getElementById('is_aos_cx');
    const aosCxOptions = document.getElementById('aos_cx_options');
    const aosCxRoutedFields = document.getElementById('aos_cx_routed_fields');
    const aosCxRadios = document.getElementsByName('aos_cx_type');
    const modeContainer = document.getElementById('mode_container');
    const modeRequiredStar = document.getElementById('mode_required_star');
    const modeHelp = document.getElementById('mode_help');
    const aosCxModeHelp = document.getElementById('aos_cx_mode_help');
    
    function toggleModeFields() {
        const mode = modeSelect.value;
        const isAosCx = isAosCxCheckbox.checked;
        let aosCxType = 'non-routed';
        for (const radio of aosCxRadios) {
            if (radio.checked) {
                aosCxType = radio.value;
                break;
            }
        }
        
        if (isAosCx) {
            aosCxOptions.style.display = 'block';
            if (aosCxType === 'routed') {
                aosCxRoutedFields.style.display = 'block';
                modeContainer.style.display = 'none';
                modeSelect.required = false;
                accessFields.style.display = 'none';
                trunkFields.style.display = 'none';
            } else {
                aosCxRoutedFields.style.display = 'none';
                modeContainer.style.display = 'block';
                modeSelect.required = true;
                modeRequiredStar.classList.remove('d-none');
            }
        } else {
            aosCxOptions.style.display = 'none';
            aosCxRoutedFields.style.display = 'none';
            modeContainer.style.display = 'block';
            modeSelect.required = true;
            modeRequiredStar.classList.remove('d-none');
        }
        
        if (!isAosCx || aosCxType === 'non-routed') {
            if (mode === 'access') {
                accessFields.style.display = 'block';
                trunkFields.style.display = 'none';
            } else if (mode === 'trunk') {
                accessFields.style.display = 'none';
                trunkFields.style.display = 'block';
            } else {
                accessFields.style.display = 'none';
                trunkFields.style.display = 'none';
            }
        }
    }
    
    modeSelect.addEventListener('change', toggleModeFields);
    isAosCxCheckbox.addEventListener('change', toggleModeFields);
    aosCxRadios.forEach(radio => radio.addEventListener('change', toggleModeFields));
    toggleModeFields();
});

document.addEventListener('DOMContentLoaded', function() {
    const noIpCheckbox = document.getElementById('no_ip_address');
    const ipAddress = document.getElementById('ip_address');
    const prefixLength = document.getElementById('prefix_length');
    
    function toggleIpFields() {
        if (noIpCheckbox.checked) {
            ipAddress.disabled = true;
            prefixLength.disabled = true;
            ipAddress.value = '';
            prefixLength.value = '';
        } else {
            ipAddress.disabled = false;
            prefixLength.disabled = false;
        }
    }
    
    noIpCheckbox.addEventListener('change', toggleIpFields);
    toggleIpFields(); // Initial state
});