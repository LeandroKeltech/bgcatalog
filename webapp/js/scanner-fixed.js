// ================================
// BARCODE SCANNER - VERSÃO CORRIGIDA
// Versão simplificada e robusta para resolver problemas de inicialização
// ================================

class BarcodeScanner {
    constructor() {
        this.isScanning = false;
        this.videoStream = null;
        this.quaggaInitialized = false;
        this.onBarcodeDetected = null;
        
        // Bind methods to preserve context
        this.handleBarcodeDetection = this.handleBarcodeDetection.bind(this);
        this.handleError = this.handleError.bind(this);
    }

    /**
     * Iniciar scanner - método principal
     */
    async startScanning(onDetected) {
        console.log('🚀 Iniciando scanner...');
        
        if (this.isScanning) {
            console.log('⚠️ Scanner já está ativo');
            return;
        }

        this.onBarcodeDetected = onDetected;

        try {
            // Verificar se Quagga está disponível
            if (typeof Quagga === 'undefined') {
                throw new Error('QuaggaJS não está carregado. Verifique se a biblioteca está incluída.');
            }

            // Verificar suporte à câmera
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Câmera não suportada neste navegador');
            }

            // Mostrar modal
            const modal = document.getElementById('scanner-modal');
            if (!modal) {
                throw new Error('Modal do scanner não encontrado. Verifique se o HTML está correto.');
            }
            modal.classList.add('active');

            // Iniciar câmera
            await this.initCamera();
            
            // Inicializar Quagga
            await this.initQuagga();
            
            this.isScanning = true;
            console.log('✅ Scanner iniciado com sucesso');
            
            // Atualizar status na UI
            this.updateScannerStatus('📱 Posicione o código de barras no quadro');

        } catch (error) {
            console.error('❌ Erro ao iniciar scanner:', error);
            this.handleError(error.message);
            this.stopScanning();
        }
    }

    /**
     * Inicializar câmera com fallbacks
     */
    async initCamera() {
        console.log('📹 Inicializando câmera...');
        
        const video = document.getElementById('scanner-video');
        if (!video) {
            throw new Error('Elemento de vídeo não encontrado');
        }

        // Configurações da câmera com fallbacks
        const constraints = {
            video: {
                facingMode: 'environment', // Câmera traseira
                width: { ideal: 1280, min: 640 },
                height: { ideal: 720, min: 480 }
            }
        };

        try {
            // Tentar com câmera traseira primeiro
            console.log('📱 Tentando câmera traseira...');
            this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (envError) {
            console.log('📱 Câmera traseira falhou, tentando qualquer câmera...');
            try {
                // Fallback: qualquer câmera disponível
                constraints.video = { width: { ideal: 640 }, height: { ideal: 480 } };
                this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (anyError) {
                throw new Error(`Falha ao acessar câmera: ${anyError.message}`);
            }
        }

        // Configurar elemento de vídeo
        video.srcObject = this.videoStream;
        
        // Aguardar vídeo carregar
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout ao carregar vídeo'));
            }, 5000);
            
            video.onloadedmetadata = () => {
                clearTimeout(timeout);
                console.log(`📹 Vídeo carregado: ${video.videoWidth}x${video.videoHeight}`);
                resolve();
            };
            
            video.onerror = () => {
                clearTimeout(timeout);
                reject(new Error('Erro ao carregar vídeo'));
            };
        });
    }

    /**
     * Inicializar Quagga com configuração otimizada
     */
    async initQuagga() {
        return new Promise((resolve, reject) => {
            console.log('🔍 Inicializando detector Quagga...');
            
            const config = {
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
                        "ean_reader",      // EAN-13, EAN-8
                        "upc_reader",      // UPC-A
                        "upc_e_reader",    // UPC-E  
                        "code_128_reader", // Code 128
                        "code_39_reader"   // Code 39
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
                    halfSample: true
                },
                numOfWorkers: 1,
                frequency: 20
            };

            Quagga.init(config, (err) => {
                if (err) {
                    console.error('❌ Erro ao inicializar Quagga:', err);
                    reject(new Error(`Falha na inicialização do scanner: ${err.message}`));
                    return;
                }

                console.log('✅ Quagga inicializado');
                
                // Configurar listeners
                Quagga.onDetected(this.handleBarcodeDetection);
                
                // Iniciar detecção
                Quagga.start();
                this.quaggaInitialized = true;
                
                resolve();
            });
        });
    }

    /**
     * Lidar com detecção de código de barras
     */
    handleBarcodeDetection(result) {
        const code = result.codeResult.code;
        console.log('🔍 Código detectado:', code);
        
        // Atualizar status
        this.updateScannerStatus(`🔍 Código detectado: ${code}`);
        
        // Validar código
        if (this.isValidBarcode(code)) {
            console.log('✅ Código válido:', code);
            
            // Mostrar sucesso
            this.updateScannerStatus(`✅ Código válido: ${code}`);
            
            // Parar scanner após delay
            setTimeout(() => {
                this.stopScanning();
                
                // Chamar callback
                if (this.onBarcodeDetected) {
                    this.onBarcodeDetected(code);
                }
            }, 1000);
            
        } else {
            console.log('❌ Código inválido, continuando...', code);
            this.updateScannerStatus('❌ Código inválido, tentando novamente...');
            
            // Resetar status após delay
            setTimeout(() => {
                this.updateScannerStatus('📱 Posicione o código de barras no quadro');
            }, 2000);
        }
    }

    /**
     * Validar código de barras
     */
    isValidBarcode(code) {
        if (!code || typeof code !== 'string') return false;
        
        const cleanCode = code.trim();
        const digitCount = (cleanCode.match(/\d/g) || []).length;
        const totalLength = cleanCode.length;
        
        // Deve ter pelo menos 50% dígitos
        if (digitCount < totalLength * 0.5) return false;
        
        // Validação de comprimento
        if (totalLength < 6 || totalLength > 18) return false;
        
        // Padrões comuns
        const patterns = [
            /^\d{8}$/,          // EAN-8
            /^\d{12}$/,         // UPC-A
            /^\d{13}$/,         // EAN-13
            /^[\dA-Z\-\. ]+$/   // Code 39/128
        ];
        
        return patterns.some(pattern => pattern.test(cleanCode));
    }

    /**
     * Atualizar status na interface
     */
    updateScannerStatus(message) {
        const statusElement = document.getElementById('scanner-status');
        const hintElement = statusElement?.querySelector('.scanner-hint');
        
        if (hintElement) {
            hintElement.textContent = message;
        } else {
            console.log('Scanner Status:', message);
        }
    }

    /**
     * Parar scanner
     */
    stopScanning() {
        console.log('🛑 Parando scanner...');
        
        // Esconder modal
        const modal = document.getElementById('scanner-modal');
        if (modal) {
            modal.classList.remove('active');
        }

        // Parar Quagga
        if (this.quaggaInitialized) {
            try {
                Quagga.stop();
                Quagga.offDetected(this.handleBarcodeDetection);
                this.quaggaInitialized = false;
                console.log('✅ Quagga parado');
            } catch (error) {
                console.error('❌ Erro ao parar Quagga:', error);
            }
        }

        // Parar stream de vídeo
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => {
                track.stop();
            });
            this.videoStream = null;
            console.log('✅ Stream de vídeo parado');
        }

        this.isScanning = false;
        this.onBarcodeDetected = null;
        
        console.log('✅ Scanner parado completamente');
    }

    /**
     * Lidar com erros
     */
    handleError(message) {
        console.error('❌ Erro do scanner:', message);
        
        // Mostrar erro via toast se disponível
        if (typeof showToast === 'function') {
            showToast(`❌ ${message}`, 'error');
        } else {
            alert(`Erro do Scanner: ${message}`);
        }
    }

    /**
     * Entrada manual como fallback
     */
    promptManualInput() {
        const barcode = prompt('Digite o código de barras manualmente:');
        if (barcode && barcode.trim()) {
            const cleanBarcode = barcode.trim();
            console.log('✏️ Código manual:', cleanBarcode);
            if (this.onBarcodeDetected) {
                this.onBarcodeDetected(cleanBarcode);
            }
            return cleanBarcode;
        }
        return null;
    }

    /**
     * Verificar disponibilidade da câmera
     */
    static async isCameraAvailable() {
        try {
            if (!navigator.mediaDevices?.getUserMedia) {
                return false;
            }
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.some(device => device.kind === 'videoinput');
        } catch (error) {
            console.error('Erro ao verificar câmera:', error);
            return false;
        }
    }
}

// ================================
// INSTÂNCIA GLOBAL E FUNÇÕES
// ================================

// Criar instância global
const barcodeScanner = new BarcodeScanner();

// Função global para iniciar scanner
function startBarcodeScanner() {
    console.log('🚀 Iniciando scanner via função global...');
    
    barcodeScanner.startScanning((barcode) => {
        console.log('📊 Resultado do scanner:', barcode);
        
        // Chamar função de resultado se existir
        if (typeof handleBarcodeResult === 'function') {
            handleBarcodeResult(barcode);
        }
        
        // Mostrar toast se disponível
        if (typeof showToast === 'function') {
            showToast(`✅ Código escaneado: ${barcode}`, 'success');
        } else {
            console.log(`✅ Código escaneado: ${barcode}`);
        }
    }).catch(error => {
        console.error('❌ Erro fatal do scanner:', error);
        if (typeof showToast === 'function') {
            showToast(`❌ Erro: ${error.message}`, 'error');
        }
    });
}

// Função global para parar scanner
function stopBarcodeScanner() {
    barcodeScanner.stopScanning();
}

// Função global para entrada manual
function manualBarcodeInput() {
    barcodeScanner.stopScanning();
    const barcode = barcodeScanner.promptManualInput();
    if (barcode && typeof handleBarcodeResult === 'function') {
        handleBarcodeResult(barcode);
    }
}

// Função para verificar se tudo está funcionando
function testScannerSetup() {
    console.log('🧪 Testando configuração do scanner...');
    
    const checks = {
        quagga: typeof Quagga !== 'undefined',
        camera: !!navigator.mediaDevices?.getUserMedia,
        modal: !!document.getElementById('scanner-modal'),
        video: !!document.getElementById('scanner-video')
    };
    
    console.log('📋 Verificações:', checks);
    
    const allOk = Object.values(checks).every(check => check);
    
    if (allOk) {
        console.log('✅ Tudo configurado corretamente!');
        if (typeof showToast === 'function') {
            showToast('✅ Scanner configurado corretamente', 'success');
        }
    } else {
        const missing = Object.entries(checks)
            .filter(([_, value]) => !value)
            .map(([key, _]) => key);
        console.error('❌ Problemas encontrados:', missing);
        if (typeof showToast === 'function') {
            showToast(`❌ Problemas: ${missing.join(', ')}`, 'error');
        }
    }
    
    return allOk;
}

// Função de fallback para handleBarcodeResult se não existir
function handleBarcodeResult(barcode) {
    console.log('📊 Código recebido:', barcode);
    
    // Se existe um elemento de input com id 'barcode', preencher
    const barcodeInput = document.getElementById('barcode');
    if (barcodeInput) {
        barcodeInput.value = barcode;
        console.log('✅ Código inserido no campo de entrada');
    }
}

// Auto-teste quando carregar
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔧 Scanner carregado, executando auto-teste...');
    setTimeout(testScannerSetup, 1000);
});

console.log('🎯 Scanner de código de barras carregado - Versão Corrigida v1.0');