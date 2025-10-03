// ================================
// PHOTO BARCODE SCANNER MODULE
// ================================

class PhotoBarcodeScanner {
    constructor() {
        this.videoStream = null;
        this.capturedImageData = null;
        this.isProcessing = false;
    }

    // Open photo modal and start camera
    async openPhotoModal() {
        const modal = document.getElementById('photo-modal');
        modal.classList.add('active');
        
        try {
            await this.startCamera();
        } catch (error) {
            console.error('Error starting camera:', error);
            this.showPhotoError('Erro ao acessar câmera: ' + error.message);
        }
    }

    // Start camera for photo capture
    async startCamera() {
        const video = document.getElementById('photo-video');
        const preview = document.getElementById('photo-preview');
        
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            video.srcObject = this.videoStream;
            video.style.display = 'block';
            preview.style.display = 'none';
            
            // Show capture button
            document.getElementById('capture-btn').style.display = 'flex';
            document.getElementById('process-btn').style.display = 'none';
            document.getElementById('retake-btn').style.display = 'none';
            
        } catch (error) {
            throw new Error('Não foi possível acessar a câmera. Verifique as permissões.');
        }
    }

    // Capture photo from video
    async capturePhoto() {
        const video = document.getElementById('photo-video');
        const canvas = document.getElementById('photo-canvas');
        const preview = document.getElementById('photo-preview');
        
        if (!this.videoStream) {
            this.showPhotoError('Câmera não iniciada');
            return;
        }

        // Set canvas size to video size
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        
        // Convert to image data
        this.capturedImageData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Show captured image
        preview.innerHTML = `<img src="${this.capturedImageData}" alt="Foto capturada">`;
        preview.style.display = 'flex';
        video.style.display = 'none';
        
        // Stop camera stream
        this.stopCamera();
        
        // Update buttons
        document.getElementById('capture-btn').style.display = 'none';
        document.getElementById('process-btn').style.display = 'flex';
        document.getElementById('retake-btn').style.display = 'flex';
        
        showToast('📸 Foto capturada! Clique em "Processar" para ler o código.', 'success');
    }

    // Process captured photo for barcode
    async processPhoto() {
        if (!this.capturedImageData) {
            this.showPhotoError('Nenhuma foto capturada');
            return;
        }

        if (this.isProcessing) {
            return;
        }

        this.isProcessing = true;
        this.showProcessingIndicator(true);
        
        try {
            // Create image element from captured data
            const img = new Image();
            img.onload = () => {
                this.analyzeImageForBarcode(img);
            };
            img.src = this.capturedImageData;
            
        } catch (error) {
            console.error('Error processing photo:', error);
            this.showPhotoError('Erro ao processar foto: ' + error.message);
            this.isProcessing = false;
            this.showProcessingIndicator(false);
        }
    }

    // Analyze image for barcode using Quagga
    analyzeImageForBarcode(img) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        // Use Quagga to decode barcode from image
        Quagga.decodeSingle({
            src: this.capturedImageData,
            numOfWorkers: 1,
            inputStream: {
                size: Math.min(img.width, img.height)
            },
            decoder: {
                readers: [
                    "ean_reader",
                    "upc_reader", 
                    "upc_e_reader",
                    "code_128_reader",
                    "code_39_reader",
                    "i2of5_reader"
                ]
            },
            locate: true,
            locator: {
                patchSize: "large",
                halfSample: false
            }
        }, (result) => {
            this.isProcessing = false;
            this.showProcessingIndicator(false);
            
            if (result && result.codeResult) {
                const barcode = result.codeResult.code;
                console.log('📸 Barcode found in photo:', barcode);
                
                // Validate barcode
                if (this.isValidBarcode(barcode)) {
                    this.closePhotoModal();
                    handleBarcodeResult(barcode);
                    showToast('✅ Código encontrado: ' + barcode, 'success');
                } else {
                    this.showPhotoError('Código inválido encontrado: ' + barcode);
                }
            } else {
                this.showPhotoError('❌ Nenhum código de barras encontrado na foto.\n\nDicas:\n• Certifique-se que o código está nítido\n• Tente com melhor iluminação\n• Aproxime mais o código\n• Tente um ângulo diferente');
            }
        });
    }

    // Validate barcode (reuse from scanner.js)
    isValidBarcode(code) {
        if (!code || typeof code !== 'string') return false;
        
        const cleanCode = code.trim();
        const digitCount = (cleanCode.match(/\d/g) || []).length;
        const totalLength = cleanCode.length;
        
        if (digitCount < totalLength * 0.5) return false;
        if (totalLength < 6 || totalLength > 20) return false;
        
        const patterns = [
            /^\d{8}$/,          // EAN-8
            /^\d{12}$/,         // UPC-A
            /^\d{13}$/,         // EAN-13
            /^[\dA-Z\-\. ]+$/   // Code 39/128
        ];
        
        return patterns.some(pattern => pattern.test(cleanCode));
    }

    // Retake photo
    async retakePhoto() {
        const preview = document.getElementById('photo-preview');
        preview.innerHTML = `
            <div class="photo-placeholder">
                <span class="material-icons">photo_camera</span>
                <p>Clique para tirar uma foto do código de barras</p>
            </div>
        `;
        
        this.capturedImageData = null;
        await this.startCamera();
    }

    // Stop camera stream
    stopCamera() {
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
    }

    // Close photo modal
    closePhotoModal() {
        const modal = document.getElementById('photo-modal');
        modal.classList.remove('active');
        
        this.stopCamera();
        this.capturedImageData = null;
        this.isProcessing = false;
        
        // Reset UI
        const video = document.getElementById('photo-video');
        const preview = document.getElementById('photo-preview');
        
        video.style.display = 'none';
        preview.style.display = 'flex';
        preview.innerHTML = `
            <div class="photo-placeholder">
                <span class="material-icons">photo_camera</span>
                <p>Clique para tirar uma foto do código de barras</p>
            </div>
        `;
        
        document.getElementById('capture-btn').style.display = 'flex';
        document.getElementById('process-btn').style.display = 'none';
        document.getElementById('retake-btn').style.display = 'none';
    }

    // Show processing indicator
    showProcessingIndicator(show) {
        const container = document.querySelector('.photo-container');
        
        if (show) {
            const indicator = document.createElement('div');
            indicator.className = 'photo-processing';
            indicator.innerHTML = `
                <span class="material-icons spinning">search</span>
                <span>Processando foto...</span>
            `;
            container.appendChild(indicator);
        } else {
            const existing = container.querySelector('.photo-processing');
            if (existing) {
                existing.remove();
            }
        }
    }

    // Show photo error
    showPhotoError(message) {
        showToast(message, 'error');
    }
}

// Global photo scanner instance
const photoBarcodeScanner = new PhotoBarcodeScanner();

// Global functions for HTML
function takeBarcodePhoto() {
    photoBarcodeScanner.openPhotoModal();
}

function capturePhoto() {
    photoBarcodeScanner.capturePhoto();
}

function processPhoto() {
    photoBarcodeScanner.processPhoto();
}

function retakePhoto() {
    photoBarcodeScanner.retakePhoto();
}

function closePhotoModal() {
    photoBarcodeScanner.closePhotoModal();
}