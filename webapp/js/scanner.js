// ================================
// BARCODE SCANNER MODULE
// ================================

class BarcodeScanner {
    constructor() {
        this.isScanning = false;
        this.videoStream = null;
        this.quaggaInitialized = false;
        this.onBarcodeDetected = null;
    }

    // Start barcode scanning
    async startScanning(onDetected) {
        if (this.isScanning) {
            console.log('Scanner already active');
            return;
        }

        this.onBarcodeDetected = onDetected;

        // Check camera availability
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera not available on this device');
        }

        try {
            // Show scanner modal
            const modal = document.getElementById('scanner-modal');
            modal.classList.add('active');

            // Request camera permissions
            const constraints = {
                video: {
                    facingMode: 'environment', // Prefer back camera
                    width: { ideal: 1280, min: 640 },
                    height: { ideal: 720, min: 480 }
                }
            };

            try {
                // Try with environment camera first
                this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (envError) {
                console.log('Environment camera failed, trying any camera...');
                // Fallback to any available camera
                constraints.video = {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                };
                this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            }

            // Set up video element
            const video = document.getElementById('scanner-video');
            video.srcObject = this.videoStream;

            // Wait for video to be ready
            await new Promise((resolve) => {
                video.onloadedmetadata = resolve;
            });

            // Initialize Quagga scanner
            await this.initQuagga();
            
            this.isScanning = true;
            console.log('Barcode scanner started successfully');

        } catch (error) {
            console.error('Camera access error:', error);
            this.stopScanning();
            
            // Handle specific error types
            let errorMessage = 'Failed to access camera. ';
            if (error.name === 'NotAllowedError') {
                errorMessage += 'Please allow camera permissions and try again.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found on this device.';
            } else if (error.name === 'NotSupportedError') {
                errorMessage += 'Camera not supported in this browser.';
            } else {
                errorMessage += error.message;
            }
            
            throw new Error(errorMessage);
        }
    }

    // Initialize Quagga barcode scanner
    async initQuagga() {
        return new Promise((resolve, reject) => {
            Quagga.init({
                inputStream: {
                    name: "Live",
                    type: "LiveStream",
                    target: document.querySelector('#scanner-video'),
                    constraints: {
                        width: { min: 640, ideal: 1280 },
                        height: { min: 480, ideal: 720 },
                        facingMode: "environment"
                    }
                },
                decoder: {
                    readers: [
                        "code_128_reader",
                        "ean_reader",
                        "ean_8_reader", 
                        "code_39_reader",
                        "code_39_vin_reader",
                        "codabar_reader",
                        "upc_reader",
                        "upc_e_reader",
                        "i2of5_reader",
                        "2of5_reader"
                    ],
                    debug: {
                        drawBoundingBox: false,
                        showFrequency: false,
                        drawScanline: false,
                        showPattern: false
                    }
                },
                locate: true,
                locator: {
                    patchSize: "medium",
                    halfSample: true,
                    showCanvas: false,
                    showPatches: false,
                    showFoundPatches: false,
                    showSkeleton: false,
                    showLabels: false,
                    showPatchLabels: false,
                    showRemainingPatchLabels: false,
                    boxFromPatches: {
                        showTransformed: false,
                        showTransformedBox: false,
                        showBB: false
                    }
                },
                numOfWorkers: 2,
                frequency: 10,
                area: {
                    top: "20%",
                    right: "20%",
                    left: "20%",
                    bottom: "20%"
                }
            }, (err) => {
                if (err) {
                    console.error('Quagga initialization error:', err);
                    reject(err);
                    return;
                }

                console.log("Quagga initialization finished");
                Quagga.start();
                this.quaggaInitialized = true;

                // Listen for barcode detection
                Quagga.onDetected(this.handleBarcodeDetection.bind(this));
                resolve();
            });
        });
    }

    // Handle barcode detection
    handleBarcodeDetection(result) {
        const code = result.codeResult.code;
        
        // Validate barcode (basic validation)
        if (this.isValidBarcode(code)) {
            console.log('Valid barcode detected:', code);
            
            // Stop scanning
            this.stopScanning();
            
            // Call callback
            if (this.onBarcodeDetected) {
                this.onBarcodeDetected(code);
            }
        } else {
            console.log('Invalid barcode detected, continuing scan:', code);
        }
    }

    // Basic barcode validation
    isValidBarcode(code) {
        // Remove any non-digit characters for validation
        const digits = code.replace(/\D/g, '');
        
        // Check minimum length (most barcodes are at least 8 digits)
        if (digits.length < 8) {
            return false;
        }
        
        // Check maximum length (prevent extremely long false positives)
        if (digits.length > 18) {
            return false;
        }
        
        // Additional validation could include checksum verification
        return true;
    }

    // Stop barcode scanning
    stopScanning() {
        // Hide modal
        const modal = document.getElementById('scanner-modal');
        modal.classList.remove('active');

        // Stop Quagga
        if (this.quaggaInitialized) {
            try {
                Quagga.stop();
                Quagga.offDetected();
                this.quaggaInitialized = false;
                console.log('Quagga stopped');
            } catch (error) {
                console.error('Error stopping Quagga:', error);
            }
        }

        // Stop video stream
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => {
                track.stop();
            });
            this.videoStream = null;
            console.log('Video stream stopped');
        }

        this.isScanning = false;
        this.onBarcodeDetected = null;
    }

    // Toggle flashlight (if supported)
    async toggleFlashlight() {
        if (!this.videoStream) {
            console.log('No video stream available for flashlight');
            return false;
        }

        try {
            const track = this.videoStream.getVideoTracks()[0];
            const capabilities = track.getCapabilities();

            if (capabilities.torch) {
                const settings = track.getSettings();
                const newTorchState = !settings.torch;
                
                await track.applyConstraints({
                    advanced: [{ torch: newTorchState }]
                });
                
                console.log('Flashlight toggled:', newTorchState);
                return newTorchState;
            } else {
                console.log('Flashlight not supported on this device');
                return false;
            }
        } catch (error) {
            console.error('Error toggling flashlight:', error);
            return false;
        }
    }

    // Manual barcode input prompt
    promptManualInput() {
        const barcode = prompt('Digite o código de barras manualmente:');
        if (barcode && barcode.trim()) {
            const cleanBarcode = barcode.trim();
            if (this.onBarcodeDetected) {
                this.onBarcodeDetected(cleanBarcode);
            }
            return cleanBarcode;
        }
        return null;
    }

    // Check if camera is available
    static async isCameraAvailable() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return false;
            }

            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.some(device => device.kind === 'videoinput');
        } catch (error) {
            console.error('Error checking camera availability:', error);
            return false;
        }
    }

    // Get available cameras
    static async getCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.filter(device => device.kind === 'videoinput');
        } catch (error) {
            console.error('Error getting cameras:', error);
            return [];
        }
    }
}

// Global scanner instance
const barcodeScanner = new BarcodeScanner();

// Global functions for HTML event handlers
function startBarcodeScanner() {
    barcodeScanner.startScanning((barcode) => {
        handleBarcodeResult(barcode);
        showToast('Código escaneado: ' + barcode, 'success');
    }).catch(error => {
        console.error('Scanner error:', error);
        showToast('Erro no scanner: ' + error.message, 'error');
    });
}

function stopBarcodeScanner() {
    barcodeScanner.stopScanning();
}

function toggleFlashlight() {
    barcodeScanner.toggleFlashlight().then(state => {
        if (state !== false) {
            showToast(state ? 'Flash ligado' : 'Flash desligado', 'info');
        } else {
            showToast('Flash não suportado neste dispositivo', 'warning');
        }
    });
}

function manualBarcodeInput() {
    barcodeScanner.stopScanning();
    const barcode = barcodeScanner.promptManualInput();
    if (barcode) {
        handleBarcodeResult(barcode);
    }
}

// Handle barcode result (to be implemented in main app)
function handleBarcodeResult(barcode) {
    // This function will be implemented in app.js
    console.log('Barcode result:', barcode);
}