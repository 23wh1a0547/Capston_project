const mongoose = require("mongoose");

const submissionSchema = new mongoose.Schema({
  assignmentId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Assignment"
  },
  studentId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Student"
  },
  status: {
    type: String,
    enum: ["Pending", "Completed"],
    default: "Pending"
  },
  submittedAt: Date
});

module.exports = mongoose.model("Submission", submissionSchema);
