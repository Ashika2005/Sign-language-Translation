const apiKey = 'AIzaSyB_qzkA81_tbsFu8WmE4UqBMlTfAyTr20A';

// Function to translate page content based on selected language
async function translatePage(targetLanguage) {
    const translatableElements = document.querySelectorAll('[data-translate]');

    // Collect the texts to be translated
    const texts = Array.from(translatableElements).map(element => element.textContent);

    try {
        // API call to Google Translate
        const response = await fetch(`https://translation.googleapis.com/language/translate/v2?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                q: texts,
                target: targetLanguage,
            }),
        });

        const data = await response.json();

        // Update the page elements with translated text
        data.data.translations.forEach((translation, index) => {
            translatableElements[index].textContent = translation.translatedText;
        });
    } catch (error) {
        console.error('Error during translation:', error);
        alert('Translation failed. Please try again.');
    }
}

// Function to load saved settings on page load
window.onload = function () {
    const savedLanguage = localStorage.getItem('language');
    if (savedLanguage) {
        translatePage(savedLanguage);
    }
};
