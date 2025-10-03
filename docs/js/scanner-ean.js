// ================================
// SCANNER EAN OTIMIZADO
// Versão especializada para códigos EAN-13 e EAN-8
// ================================

class EANBarcodeScanner {
    constructor() {
        this.isScanning = false;
        this.videoStream = null;
        this.quaggaInitialized = false;
        this.onBarcodeDetected = null;
        this.detectionHistory = new Map(); // Para evitar duplicatas
        
        // Bind methods
        this.handleBarcodeDetection = this.handleBarcodeDetection.bind(this);
        this.handleError = this.handleError.bind(this);
    }

    /**
     * Iniciar scanner EAN otimizado
     */
    async startScanning(onDetected) {
        console.log('🎯 Iniciando scanner EAN otimizado...');
        
        if (this.isScanning) {
            console.log('⚠️ Scanner já está ativo');
            return;
        }

        this.onBarcodeDetected = onDetected;
        this.detectionHistory.clear();

        try {
            // Verificações básicas
            if (typeof Quagga === 'undefined') {
                throw new Error('QuaggaJS não está carregado');
            }

            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error('Câmera não suportada neste navegador');
            }

            // Mostrar modal
            const modal = document.getElementById('scanner-modal');
            if (!modal) {
                throw new Error('Modal do scanner não encontrado');
            }
            modal.classList.add('active');

            // Iniciar câmera com configuração otimizada para EAN
            await this.initOptimizedCamera();
            
            // Inicializar Quagga com configuração EAN
            await this.initEANQuagga();
            
            this.isScanning = true;
            console.log('✅ Scanner EAN iniciado com sucesso');
            
            // Atualizar status
            this.updateScannerStatus('📱 Posicione o código EAN no quadro');

        } catch (error) {
            console.error('❌ Erro ao iniciar scanner EAN:', error);
            this.handleError(error.message);
            this.stopScanning();
        }
    }

    /**
     * Inicializar câmera com configuração otimizada para EAN
     */
    async initOptimizedCamera() {
        console.log('📹 Iniciando câmera otimizada para EAN...');
        
        const video = document.getElementById('scanner-video');
        if (!video) {
            throw new Error('Elemento de vídeo não encontrado');
        }

        // Configurações otimizadas para leitura de EAN
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { 
                    min: 800, 
                    ideal: 1280, 
                    max: 1920 
                },
                height: { 
                    min: 600, 
                    ideal: 720, 
                    max: 1080 
                },
                // Configurações específicas para melhor foco
                focusMode: 'continuous',
                exposureMode: 'continuous',
                whiteBalanceMode: 'continuous'
            }
        };

        try {
            // Tentar com câmera traseira otimizada
            this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (envError) {
            console.log('📱 Câmera traseira falhou, usando fallback...');
            // Fallback com configurações básicas
            constraints.video = {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            };
            this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        }

        // Configurar elemento de vídeo
        video.srcObject = this.videoStream;
        
        // Aguardar vídeo carregar
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout ao carregar vídeo'));
            }, 10000); // 10 segundos para carregamento
            
            video.onloadedmetadata = () => {
                clearTimeout(timeout);
                console.log(`📹 Vídeo EAN carregado: ${video.videoWidth}x${video.videoHeight}`);
                resolve();
            };
        });
    }

    /**
     * Inicializar Quagga com configuração específica para EAN
     */
    async initEANQuagga() {
        return new Promise((resolve, reject) => {
            console.log('🔍 Inicializando detector EAN...');
            
            const config = {
                inputStream: {
                    name: "Live",
                    type: "LiveStream",
                    target: document.querySelector('#scanner-video'),
                    constraints: {
                        width: { min: 800, ideal: 1280, max: 1920 },
                        height: { min: 600, ideal: 720, max: 1080 },
                        facingMode: "environment"
                    }
                },
                decoder: {
                    // APENAS leitores EAN para máxima precisão
                    readers: [
                        "ean_reader",      // EAN-13 e EAN-8 (prioridade)
                        "upc_reader",      // UPC-A (compatível com EAN)
                        "upc_e_reader"     // UPC-E (compatível com EAN)
                    ],
                    debug: {
                        drawBoundingBox: true,   // Mostrar área detectada
                        showFrequency: false,
                        drawScanline: true,      // Mostrar linha de scan
                        showPattern: false
                    }
                },
                locate: true,
                locator: {
                    patchSize: "large",      // Patches grandes para EAN
                    halfSample: false,       // Máxima qualidade
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
                numOfWorkers: 2,        // 2 workers para melhor performance
                frequency: 30,          // Alta frequência para EAN
                area: {                 // Área focada no centro
                    top: "20%",
                    right: "20%", 
                    left: "20%",
                    bottom: "20%"
                }
            };

            Quagga.init(config, (err) => {
                if (err) {
                    console.error('❌ Erro ao inicializar Quagga EAN:', err);
                    reject(new Error(`Falha na inicialização EAN: ${err.message}`));
                    return;
                }

                console.log('✅ Detector EAN inicializado');
                
                // Configurar listeners otimizados para EAN
                this.setupEANListeners();
                
                // Iniciar detecção
                Quagga.start();
                this.quaggaInitialized = true;
                
                resolve();
            });
        });
    }

    /**
     * Configurar listeners específicos para EAN
     */
    setupEANListeners() {
        // Listener principal para detecções
        Quagga.onDetected((result) => {
            const code = result.codeResult.code;
            const format = result.codeResult.format;
            
            console.log(`🎯 EAN detectado: ${code} (${format})`);
            
            // Verificar se é realmente EAN
            if (this.isEANFormat(format)) {
                this.handleEANDetection(code, result);
            }
        });

        // Listener para melhorar qualidade de detecção
        Quagga.onProcessed((result) => {
            if (result && result.codeResult) {
                const code = result.codeResult.code;
                const format = result.codeResult.format;
                const quality = result.codeResult.quality;
                
                // Aceitar apenas detecções de alta qualidade para EAN
                if (this.isEANFormat(format) && quality > 80) {
                    this.handleEANDetection(code, result);
                }
            }
        });
    }

    /**
     * Verificar se o formato é EAN
     */
    isEANFormat(format) {
        const eanFormats = ['EAN_13', 'EAN_8', 'UPC_A', 'UPC_E'];
        return eanFormats.includes(format);
    }

    /**
     * Lidar com detecção EAN
     */
    handleEANDetection(code, result) {
        const now = Date.now();
        const format = result.codeResult.format;
        
        // Evitar duplicatas recentes (últimos 2 segundos)
        if (this.detectionHistory.has(code)) {
            const lastDetection = this.detectionHistory.get(code);
            if (now - lastDetection < 2000) {
                return; // Ignorar duplicata recente
            }
        }
        
        // Atualizar histórico
        this.detectionHistory.set(code, now);
        
        // Atualizar status
        this.updateScannerStatus(`🔍 EAN detectado: ${code} (${format})`);
        
        // Validar EAN
        if (this.isValidEAN(code)) {
            console.log('✅ EAN válido:', code);
            
            // Mostrar sucesso
            this.updateScannerStatus(`✅ EAN válido: ${code}`);
            
            // Som de sucesso (se suportado)
            this.playSuccessSound();
            
            // Parar scanner após delay
            setTimeout(() => {
                this.stopScanning();
                
                // Chamar callback
                if (this.onBarcodeDetected) {
                    this.onBarcodeDetected(code);
                }
            }, 1200); // Delay maior para mostrar resultado
            
        } else {
            console.log('❌ EAN inválido, continuando...', code);
            this.updateScannerStatus('❌ EAN inválido, tentando novamente...');
            
            // Resetar status após delay
            setTimeout(() => {
                this.updateScannerStatus('📱 Posicione o código EAN no quadro');
            }, 2000);
        }
    }

    /**
     * Validar código EAN especificamente
     */
    isValidEAN(code) {
        if (!code || typeof code !== 'string') return false;
        
        const cleanCode = code.trim();
        
        // EAN deve ser apenas dígitos
        if (!/^\d+$/.test(cleanCode)) return false;
        
        // Validar comprimentos EAN
        if (cleanCode.length === 8) {
            return this.validateEAN8(cleanCode);
        } else if (cleanCode.length === 13) {
            return this.validateEAN13(cleanCode);
        } else if (cleanCode.length === 12) {
            // UPC-A (tratado como EAN-13 com zero à esquerda)
            return this.validateEAN13('0' + cleanCode);
        } else if (cleanCode.length >= 6 && cleanCode.length <= 8) {
            // UPC-E (formato compacto)
            return true; // Aceitar UPC-E sem validação checksum complexa
        }
        
        return false;
    }

    /**
     * Validar checksum EAN-8
     */
    validateEAN8(code) {
        const digits = code.split('').map(Number);
        const checksum = digits.pop();
        
        let sum = 0;
        for (let i = 0; i < digits.length; i++) {
            sum += digits[i] * (i % 2 === 0 ? 3 : 1);
        }
        
        const calculatedChecksum = (10 - (sum % 10)) % 10;
        return calculatedChecksum === checksum;
    }

    /**
     * Validar checksum EAN-13
     */
    validateEAN13(code) {
        const digits = code.split('').map(Number);
        const checksum = digits.pop();
        
        let sum = 0;
        for (let i = 0; i < digits.length; i++) {
            sum += digits[i] * (i % 2 === 0 ? 1 : 3);
        }
        
        const calculatedChecksum = (10 - (sum % 10)) % 10;
        return calculatedChecksum === checksum;
    }

    /**
     * Som de sucesso
     */
    playSuccessSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Som específico para EAN (dois bips)
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
            gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.08);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.1);
            gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
            
        } catch (error) {
            console.log('🔊 Som de sucesso EAN');
        }
    }

    /**
     * Atualizar status na interface
     */
    updateScannerStatus(message) {
        const statusElement = document.getElementById('scanner-status');
        const hintElement = statusElement?.querySelector('.scanner-hint');
        
        if (hintElement) {
            hintElement.textContent = message;
        }
        
        console.log('📱 Status:', message);
    }

    /**
     * Parar scanner
     */
    stopScanning() {
        console.log('🛑 Parando scanner EAN...');
        
        // Esconder modal
        const modal = document.getElementById('scanner-modal');
        if (modal) {
            modal.classList.remove('active');
        }

        // Parar Quagga
        if (this.quaggaInitialized) {
            try {
                Quagga.stop();
                Quagga.offDetected();
                Quagga.offProcessed();
                this.quaggaInitialized = false;
                console.log('✅ Quagga EAN parado');
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
            console.log('✅ Stream EAN parado');
        }

        this.isScanning = false;
        this.onBarcodeDetected = null;
        this.detectionHistory.clear();
        
        console.log('✅ Scanner EAN parado completamente');
    }

    /**
     * Lidar com erros
     */
    handleError(message) {
        console.error('❌ Erro do scanner EAN:', message);
        
        if (typeof showToast === 'function') {
            showToast(`❌ ${message}`, 'error');
        } else {
            alert(`Erro do Scanner EAN: ${message}`);
        }
    }

    /**
     * Entrada manual para EAN
     */
    promptManualEAN() {
        const barcode = prompt('Digite o código EAN (8 ou 13 dígitos):');
        if (barcode && barcode.trim()) {
            const cleanBarcode = barcode.trim().replace(/\D/g, ''); // Apenas dígitos
            
            if (this.isValidEAN(cleanBarcode)) {
                console.log('✏️ EAN manual válido:', cleanBarcode);
                if (this.onBarcodeDetected) {
                    this.onBarcodeDetected(cleanBarcode);
                }
                return cleanBarcode;
            } else {
                alert('Código EAN inválido! Digite apenas 8 ou 13 dígitos.');
                return this.promptManualEAN(); // Tentar novamente
            }
        }
        return null;
    }
}

// ================================
// INSTÂNCIA GLOBAL E FUNÇÕES PARA EAN
// ================================

// Criar instância global otimizada para EAN
const eanBarcodeScanner = new EANBarcodeScanner();

// Função global para iniciar scanner EAN
function startEANScanner() {
    console.log('🎯 Iniciando scanner EAN via função global...');
    
    eanBarcodeScanner.startScanning((barcode) => {
        console.log('📊 EAN detectado:', barcode);
        
        // Chamar função de resultado se existir
        if (typeof handleBarcodeResult === 'function') {
            handleBarcodeResult(barcode);
        }
        
        // Mostrar toast se disponível
        if (typeof showToast === 'function') {
            showToast(`✅ EAN escaneado: ${barcode}`, 'success');
        }
    });
}

// Substituir função global padrão para usar EAN
function startBarcodeScanner() {
    startEANScanner();
}

// Função global para parar scanner EAN
function stopBarcodeScanner() {
    eanBarcodeScanner.stopScanning();
}

// Função global para entrada manual EAN
function manualBarcodeInput() {
    eanBarcodeScanner.stopScanning();
    const barcode = eanBarcodeScanner.promptManualEAN();
    if (barcode && typeof handleBarcodeResult === 'function') {
        handleBarcodeResult(barcode);
    }
}

console.log('🎯 Scanner EAN Otimizado carregado - v1.0');