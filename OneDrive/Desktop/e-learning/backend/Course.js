const mongoose = require("mongoose");

const courseSchema = new mongoose.Schema({
  courseName: String,
  category: String,
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model("Course", courseSchema);
