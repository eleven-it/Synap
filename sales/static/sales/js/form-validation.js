/**
 * Sistema de validación avanzada para formularios
 * Incluye validación en tiempo real, feedback visual y microinteracciones
 */

class FormValidator {
    constructor() {
        this.validators = {
            email: this.validateEmail,
            phone: this.validatePhone,
            taxId: this.validateTaxId,
            url: this.validateUrl,
            required: this.validateRequired,
            minLength: this.validateMinLength,
            maxLength: this.validateMaxLength,
            numeric: this.validateNumeric,
            decimal: this.validateDecimal,
            date: this.validateDate,
            vat: this.validateVAT
        };
        
        this.init();
    }

    init() {
        this.setupFormValidation();
        this.setupRealTimeValidation();
        this.setupPasswordToggle();
        this.setupProgressBar();
    }

    setupFormValidation() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                    this.showFormErrors(form);
                } else {
                    this.showSuccessMessage(form);
                }
            });
        });
    }

    setupRealTimeValidation() {
        // Validación en tiempo real para diferentes tipos de campos
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', () => this.validateField(field));
            field.addEventListener('input', () => this.clearFieldError(field));
            
            // Validación especial para campos con patrones
            if (field.hasAttribute('data-validation')) {
                field.addEventListener('input', () => this.validateField(field));
            }
        });
    }

    setupPasswordToggle() {
        document.querySelectorAll('.password-toggle').forEach(toggle => {
            const input = toggle.querySelector('input');
            const icon = toggle.querySelector('.toggle-icon');
            
            if (input && icon) {
                icon.addEventListener('click', () => {
                    const type = input.type === 'password' ? 'text' : 'password';
                    input.type = type;
                    icon.innerHTML = type === 'password' ? 
                        '<i class="fas fa-eye"></i>' : 
                        '<i class="fas fa-eye-slash"></i>';
                });
            }
        });
    }

    setupProgressBar() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const progressBar = document.getElementById('progressBar');
            if (!progressBar) return;

            const fields = form.querySelectorAll('input, select, textarea');
            const requiredFields = form.querySelectorAll('[required]');
            
            form.addEventListener('input', () => {
                const filledFields = Array.from(requiredFields).filter(field => 
                    field.value.trim() !== ''
                ).length;
                
                const progress = (filledFields / requiredFields.length) * 100;
                this.updateProgressBar(progress);
            });
        });
    }

    validateForm(form) {
        let isValid = true;
        const fields = form.querySelectorAll('input, select, textarea');
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const validations = this.getFieldValidations(field);
        let isValid = true;

        validations.forEach(validation => {
            if (!this.validators[validation.type](field, validation.value)) {
                this.showFieldError(field, validation.message);
                isValid = false;
            }
        });

        if (isValid) {
            this.clearFieldError(field);
            this.showFieldSuccess(field);
        }

        return isValid;
    }

    getFieldValidations(field) {
        const validations = [];
        
        // Validación required
        if (field.hasAttribute('required')) {
            validations.push({
                type: 'required',
                message: 'Este campo es obligatorio'
            });
        }

        // Validación por tipo de campo
        const fieldType = field.type;
        if (fieldType === 'email') {
            validations.push({
                type: 'email',
                message: 'Ingrese un email válido'
            });
        } else if (fieldType === 'tel') {
            validations.push({
                type: 'phone',
                message: 'Ingrese un número de teléfono válido'
            });
        } else if (fieldType === 'url') {
            validations.push({
                type: 'url',
                message: 'Ingrese una URL válida'
            });
        } else if (fieldType === 'number') {
            validations.push({
                type: 'numeric',
                message: 'Ingrese un número válido'
            });
        } else if (fieldType === 'date') {
            validations.push({
                type: 'date',
                message: 'Ingrese una fecha válida'
            });
        }

        // Validaciones personalizadas
        if (field.hasAttribute('data-validation')) {
            const customValidations = JSON.parse(field.getAttribute('data-validation'));
            validations.push(...customValidations);
        }

        // Validación de longitud mínima
        if (field.hasAttribute('minlength')) {
            validations.push({
                type: 'minLength',
                value: parseInt(field.getAttribute('minlength')),
                message: `Mínimo ${field.getAttribute('minlength')} caracteres`
            });
        }

        // Validación de longitud máxima
        if (field.hasAttribute('maxlength')) {
            validations.push({
                type: 'maxLength',
                value: parseInt(field.getAttribute('maxlength')),
                message: `Máximo ${field.getAttribute('maxlength')} caracteres`
            });
        }

        // Validación especial para VAT/Tax ID
        if (field.name === 'tax_id' && field.value) {
            validations.push({
                type: 'vat',
                message: 'Ingrese un ID fiscal válido'
            });
        }

        return validations;
    }

    // Validadores específicos
    validateRequired(field) {
        return field.value.trim() !== '';
    }

    validateEmail(field) {
        const email = field.value.trim();
        if (!email) return true; // Campo vacío no es error si no es required
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    validatePhone(field) {
        const phone = field.value.trim();
        if (!phone) return true;
        
        const cleanPhone = phone.replace(/[\s\-\(\)\+]/g, '');
        return /^\d{7,15}$/.test(cleanPhone);
    }

    validateUrl(field) {
        const url = field.value.trim();
        if (!url) return true;
        
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    validateNumeric(field) {
        const value = field.value.trim();
        if (!value) return true;
        
        return !isNaN(value) && !isNaN(parseFloat(value));
    }

    validateDecimal(field, decimals = 2) {
        const value = field.value.trim();
        if (!value) return true;
        
        const regex = new RegExp(`^\\d+(\\.\\d{1,${decimals}})?$`);
        return regex.test(value);
    }

    validateDate(field) {
        const date = field.value.trim();
        if (!date) return true;
        
        const dateObj = new Date(date);
        return dateObj instanceof Date && !isNaN(dateObj);
    }

    validateMinLength(field, minLength) {
        const value = field.value.trim();
        if (!value) return true;
        
        return value.length >= minLength;
    }

    validateMaxLength(field, maxLength) {
        const value = field.value.trim();
        if (!value) return true;
        
        return value.length <= maxLength;
    }

    validateVAT(field) {
        const vat = field.value.trim();
        if (!vat) return true;
        
        // Validaciones básicas para diferentes países
        const vatPatterns = {
            // España
            'ES': /^[A-Z]\d{8}$/,
            // México
            'MX': /^[A-Z]{3,4}\d{6}[A-Z0-9]{3}$/,
            // Brasil
            'BR': /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/,
            // Argentina
            'AR': /^\d{2}-\d{8}-\d$/,
            // Chile
            'CL': /^\d{1,2}\.\d{3}\.\d{3}-[0-9kK]$/,
            // Colombia
            'CO': /^\d{9,10}$/,
            // Perú
            'PE': /^\d{11}$/,
            // Estados Unidos (EIN)
            'US': /^\d{2}-\d{7}$/
        };

        // Detectar país basado en el contexto o formato
        for (const [country, pattern] of Object.entries(vatPatterns)) {
            if (pattern.test(vat)) {
                return true;
            }
        }

        // Si no coincide con ningún patrón específico, validación básica
        return vat.length >= 3 && /^[A-Z0-9\-\.]+$/i.test(vat);
    }

    validateTaxId(field) {
        const taxId = field.value.trim();
        if (!taxId) return true;
        
        return taxId.length >= 3;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        // Aplicar estilos de error
        field.classList.add('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
        
        // Crear mensaje de error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-red-500 text-sm mt-1 flex items-center animate-fade-in';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>${message}`;
        errorDiv.id = `error-${field.id || field.name}`;
        
        // Insertar después del campo
        const fieldContainer = field.closest('.form-group') || field.parentNode;
        fieldContainer.appendChild(errorDiv);
        
        // Animación de shake
        field.classList.add('animate-shake');
        setTimeout(() => {
            field.classList.remove('animate-shake');
        }, 500);
        
        // Sonido de error (opcional)
        this.playErrorSound();
    }

    clearFieldError(field) {
        field.classList.remove('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
        
        const errorDiv = field.parentNode.querySelector(`#error-${field.id || field.name}`);
        if (errorDiv) {
            errorDiv.classList.add('animate-fade-out');
            setTimeout(() => errorDiv.remove(), 200);
        }
    }

    showFieldSuccess(field) {
        // Aplicar estilos de éxito temporalmente
        field.classList.add('border-green-500', 'focus:border-green-500', 'focus:ring-green-500');
        
        setTimeout(() => {
            field.classList.remove('border-green-500', 'focus:border-green-500', 'focus:ring-green-500');
        }, 1000);
    }

    showFormErrors(form) {
        // Contar errores
        const errors = form.querySelectorAll('.border-red-500');
        const errorCount = errors.length;
        
        // Mostrar toast de error
        this.showToast(`Por favor, corrija ${errorCount} error${errorCount > 1 ? 'es' : ''} en el formulario`, 'error');
        
        // Scroll al primer error
        if (errors.length > 0) {
            errors[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        // Efecto visual en el formulario
        form.classList.add('animate-shake');
        setTimeout(() => {
            form.classList.remove('animate-shake');
        }, 500);
    }

    showSuccessMessage(form) {
        this.showToast('Formulario enviado correctamente', 'success');
        
        // Efecto de confeti (opcional)
        this.showConfetti();
    }

    updateProgressBar(progress) {
        const progressBar = document.getElementById('progressBar');
        if (!progressBar) return;
        
        progressBar.style.transform = `scaleX(${progress / 100})`;
        
        if (progress > 0) {
            progressBar.classList.add('active');
        } else {
            progressBar.classList.remove('active');
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 transform transition-all duration-300 translate-x-full`;
        
        const icon = type === 'error' ? 'fa-exclamation-circle' : 
                    type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
        
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 'bg-blue-500';
        
        toast.innerHTML = `
            <div class="flex items-center ${bgColor} text-white p-4 rounded-lg shadow-lg max-w-sm">
                <i class="fas ${icon} mr-3 text-lg"></i>
                <span class="flex-1">${message}</span>
                <button class="ml-3 text-white hover:text-gray-200 transition-colors" 
                        onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    showConfetti() {
        // Crear confeti simple
        for (let i = 0; i < 50; i++) {
            setTimeout(() => {
                const confetti = document.createElement('div');
                confetti.className = 'fixed z-50 w-2 h-2 rounded-full animate-bounce';
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.top = '-10px';
                confetti.style.backgroundColor = ['#f97316', '#ef4444', '#10b981', '#3b82f6', '#8b5cf6'][Math.floor(Math.random() * 5)];
                
                document.body.appendChild(confetti);
                
                // Animar caída
                confetti.animate([
                    { transform: 'translateY(0px) rotate(0deg)', opacity: 1 },
                    { transform: `translateY(${window.innerHeight}px) rotate(360deg)`, opacity: 0 }
                ], {
                    duration: 3000,
                    easing: 'ease-out'
                }).onfinish = () => confetti.remove();
            }, i * 100);
        }
    }

    playErrorSound() {
        // Crear un beep simple usando Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            // Fallback silencioso si no se puede reproducir sonido
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.formValidator = new FormValidator();
});

// CSS para animaciones adicionales
const additionalStyle = document.createElement('style');
additionalStyle.textContent = `
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fade-out {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-10px); }
    }
    
    .animate-fade-in {
        animation: fade-in 0.3s ease-out;
    }
    
    .animate-fade-out {
        animation: fade-out 0.2s ease-out;
    }
    
    .animate-shake {
        animation: shake 0.5s ease-in-out;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    .form-group {
        transition: all 0.3s ease;
    }
    
    .form-group:focus-within {
        transform: translateY(-2px);
    }
    
    .input-focus-ring {
        transition: all 0.2s ease;
    }
    
    .input-focus-ring:focus {
        transform: scale(1.02);
        box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
    }
`;
document.head.appendChild(additionalStyle); 