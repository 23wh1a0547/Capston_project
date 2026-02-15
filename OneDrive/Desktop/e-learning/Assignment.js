const mongoose = require("mongoose");

const assignmentSchema = new mongoose.Schema({
  title: String,
  courseId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Course"
  },
  dueDate: Date,
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model("Assignment", assignmentSchema);
