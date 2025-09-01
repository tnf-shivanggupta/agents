// Install dependencies first:
// npm install axios dotenv

const axios = require('axios');
require('dotenv').config();

const GROQ_BASE_URL = "https://api.groq.com/openai/v1";
const groqApiKey = process.env.GROQ_API_KEY;
async function askGroq(messages) {
  try {
    const response = await axios.post(
      `${GROQ_BASE_URL}/chat/completions`,
      {
        model: "llama3-8b-8192",
        messages: messages
      },
      {
        headers: {
          "Authorization": `Bearer ${groqApiKey}`,
          "Content-Type": "application/json"
        }
      }
    );
    console.log(response.data.choices[0].message.content);
    return response.data.choices[0].message.content;
  } catch (error) {
    console.error(error.response ? error.response.data : error.message);
  }
}

// Example usage:
const messages = [
  { role: "system", content: "You are a helpful assistant for english to hindi translator. Don't reply to any question other than translation. Reply calmly." },
  { role: "user", content: "Translate the following English text to Hindi: 'Hello, how are you?'" }
];

askGroq(messages);