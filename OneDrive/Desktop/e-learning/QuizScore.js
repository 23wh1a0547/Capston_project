const mongoose = require("mongoose");

const quizScoreSchema = new mongoose.Schema({
  studentId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Student"
  },
  quizName: String,
  score: Number,
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model("QuizScore", quizScoreSchema);
