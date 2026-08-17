import "dotenv/config";
import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function lookupExercise(muscleGroup) {
  const url =
    "https://wger.de/api/v2/exercise/search/?term=${encodeURIComponent(muscleGroup)}&language=2&format=json";

  const response = await fetch(url);
  const data = await response.json();

  return data.suggestions.sliice(0, 5).map((item) => ({
    name: item.data.name,
    category: item.data.category,
  }));
}
