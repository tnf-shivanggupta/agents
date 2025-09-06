const sendgrid = require('@sendgrid/mail');
const { Agent, functionTool } = require('./agents');

const sendEmail = functionTool(async function(subject, htmlBody) {
    sendgrid.setApiKey(process.env.SENDGRID_API_KEY);
    
    const msg = {
        to: 'ed.donner@gmail.com', // put your recipient here
        from: 'ed@edwarddonner.com', // put your verified sender here
        subject: subject,
        html: htmlBody,
    };
    
    try {
        const response = await sendgrid.send(msg);
        console.log('Email response', response[0].statusCode);
        return { status: 'success' };
    } catch (error) {
        console.error('Email send error:', error);
        return { status: 'error', message: error.message };
    }
});

const INSTRUCTIONS = `You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line.`;

const emailAgent = new Agent({
    name: "Email agent",
    instructions: INSTRUCTIONS,
    tools: [sendEmail],
    model: "gpt-4o-mini",
});

module.exports = { emailAgent, sendEmail };