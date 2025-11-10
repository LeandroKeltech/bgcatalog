// Barcode Scanner using QuaggaJS

document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('startScanner');
    const stopButton = document.getElementById('stopScanner');
    const scannerContainer = document.getElementById('scanner-container');
    const searchInput = document.getElementById('searchInput');
    
    if (!startButton) return;
    
    let scannerInitialized = false;
    
    startButton.addEventListener('click', function() {
        scannerContainer.style.display = 'block';
        
        if (!scannerInitialized) {
            Quagga.init({
                inputStream: {
                    name: "Live",
                    type: "LiveStream",
                    target: document.querySelector('#interactive'),
                    constraints: {
                        width: 640,
                        height: 480,
                        facingMode: "environment"
                    },
                },
                decoder: {
                    readers: [
                        "ean_reader",
                        "ean_8_reader",
                        "upc_reader",
                        "upc_e_reader"
                    ]
                },
            }, function(err) {
                if (err) {
                    console.error('Scanner initialization error:', err);
                    alert('Failed to start scanner. Please check camera permissions.');
                    scannerContainer.style.display = 'none';
                    return;
                }
                console.log("Scanner initialized successfully");
                Quagga.start();
                scannerInitialized = true;
            });
            
            Quagga.onDetected(function(result) {
                const code = result.codeResult.code;
                console.log("Barcode detected:", code);
                
                // Fill search input
                searchInput.value = code;
                
                // Stop scanner
                Quagga.stop();
                scannerContainer.style.display = 'none';
                
                // Auto-submit form
                searchInput.closest('form').submit();
            });
        } else {
            Quagga.start();
        }
    });
    
    if (stopButton) {
        stopButton.addEventListener('click', function() {
            Quagga.stop();
            scannerContainer.style.display = 'none';
        });
    }
});

// Cart quantity validation
document.querySelectorAll('input[type="number"]').forEach(function(input) {
    input.addEventListener('change', function() {
        const min = parseInt(this.getAttribute('min'));
        const max = parseInt(this.getAttribute('max'));
        let value = parseInt(this.value);
        
        if (value < min) this.value = min;
        if (max && value > max) this.value = max;
    });
});

// Confirm delete actions
document.querySelectorAll('a[href*="delete"]').forEach(function(link) {
    link.addEventListener('click', function(e) {
        if (!this.classList.contains('btn-danger')) return;
        
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });
});
