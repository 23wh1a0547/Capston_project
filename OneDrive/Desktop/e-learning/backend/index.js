const connectDB = require("./connect");

// Load collections
require("./Student");
require("./Course");
require("./Enrollment");
require("./Assignment");
require("./Submission");
require("./QuizScore");

connectDB();
