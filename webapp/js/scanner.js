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
            console.log('Initializing Quagga scanner...');
            
            Quagga.init({
                inputStream: {
                    name: "Live",
                    type: "LiveStream",
                    target: document.querySelector('#scanner-video'),
                    constraints: {
                        width: { min: 640, ideal: 1280, max: 1920 },
                        height: { min: 480, ideal: 720, max: 1080 },
                        facingMode: "environment"
                    }
                },
                decoder: {
                    readers: [
                        "ean_reader",      // EAN-13, EAN-8 (mais comum)
                        "upc_reader",      // UPC-A
                        "upc_e_reader",    // UPC-E
                        "code_128_reader", // Code 128
                        "code_39_reader",  // Code 39
                        "i2of5_reader"     // Interleaved 2 of 5
                    ],
                    debug: {
                        drawBoundingBox: true,  // Mostrar área detectada
                        showFrequency: false,
                        drawScanline: true,     // Mostrar linha de scan
                        showPattern: false
                    }
                },
                locate: true,
                locator: {
                    patchSize: "large",     // Patches maiores para melhor detecção
                    halfSample: false,      // Não reduzir qualidade
                    showCanvas: true,       // Mostrar canvas de debug
                    showPatches: false,
                    showFoundPatches: false,
                    showSkeleton: false,
                    showLabels: false,
                    showPatchLabels: false,
                    showRemainingPatchLabels: false,
                    boxFromPatches: {
                        showTransformed: true,
                        showTransformedBox: true,
                        showBB: true
                    }
                },
                numOfWorkers: 1,        // Reduzir workers para evitar conflitos
                frequency: 20,          // Aumentar frequência de scan
                area: {
                    top: "10%",
                    right: "10%", 
                    left: "10%",
                    bottom: "10%"
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
        
        // Update UI to show detection attempt
        this.updateScannerStatus('🔍 Código detectado: ' + code, 'scanning');
        
        // Validate barcode
        if (this.isValidBarcode(code)) {
            console.log('✅ Valid barcode detected:', code);
            
            // Show success status
            this.updateScannerStatus('✅ Código válido: ' + code, 'success');
            
            // Stop scanning after short delay
            setTimeout(() => {
                this.stopScanning();
                
                // Call callback
                if (this.onBarcodeDetected) {
                    this.onBarcodeDetected(code);
                }
            }, 800);
            
        } else {
            console.log('❌ Invalid barcode detected, continuing scan:', code);
            
            // Show error status briefly
            this.updateScannerStatus('❌ Código inválido, tentando novamente...', 'error');
            
            // Reset to scanning state after 1 second
            setTimeout(() => {
                this.updateScannerStatus('📱 Posicione o código de barras no quadro', '');
            }, 1500);
        }
    }
    
    // Update scanner status display
    updateScannerStatus(message, type = '') {
        const statusElement = document.getElementById('scanner-status');
        const hintElement = statusElement?.querySelector('.scanner-hint');
        
        if (hintElement) {
            hintElement.textContent = message;
            hintElement.className = `scanner-hint ${type}`;
        }
    }

    // Basic barcode validation
    isValidBarcode(code) {
        if (!code || typeof code !== 'string') return false;
        
        // Clean the code
        const cleanCode = code.trim();
        
        // Check if it's mostly digits (allow some letters for Code 39, Code 128)
        const digitCount = (cleanCode.match(/\d/g) || []).length;
        const totalLength = cleanCode.length;
        
        // Must be at least 50% digits
        if (digitCount < totalLength * 0.5) {
            console.log('Barcode validation failed: not enough digits', code);
            return false;
        }
        
        // Length validation (most barcodes are 6-18 characters)
        if (totalLength < 6) {
            console.log('Barcode validation failed: too short', code);
            return false;
        }
        
        if (totalLength > 20) {
            console.log('Barcode validation failed: too long', code);
            return false;
        }
        
        // Common barcode patterns
        const patterns = [
            /^\d{8}$/,          // EAN-8
            /^\d{12}$/,         // UPC-A
            /^\d{13}$/,         // EAN-13
            /^[\dA-Z\-\. ]+$/   // Code 39/128 (alphanumeric)
        ];
        
        const isValid = patterns.some(pattern => pattern.test(cleanCode));
        
        if (isValid) {
            console.log('✅ Valid barcode detected:', code);
        } else {
            console.log('❌ Invalid barcode pattern:', code);
        }
        
        return isValid;
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

function showBarcodeHelp() {
    const helpText = `
📱 DICAS PARA SCANNER DE CÓDIGO DE BARRAS:

✅ CÓDIGOS QUE FUNCIONAM:
• EAN-13 (13 dígitos) - mais comum
• EAN-8 (8 dígitos)
• UPC-A (12 dígitos)
• UPC-E (6-8 dígitos)
• Code 128, Code 39

📸 DICAS DE ESCANEAMENTO:
• Use boa iluminação
• Mantenha código reto (sem inclinação)
• Distância: 10-30cm da câmera
• Evite reflexos e sombras
• Limpe a lente da câmera

⚠️ SE NÃO FUNCIONAR:
• Use Chrome ou Safari (recomendado)
• Permita acesso à câmera
• Tente "Digitar Manualmente"
• Verifique se está em HTTPS

💡 Teste com código de barras de livro, produto ou jogo!
    `;
    
    alert(helpText);
}

// Handle barcode result (to be implemented in main app)
function handleBarcodeResult(barcode) {
    // This function will be implemented in app.js
    console.log('Barcode result:', barcode);
}