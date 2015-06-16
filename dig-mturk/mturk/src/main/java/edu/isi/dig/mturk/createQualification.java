package edu.isi.dig.mturk;

import com.amazonaws.mturk.requester.QualificationType;
import com.amazonaws.mturk.requester.QualificationTypeStatus;
import com.amazonaws.mturk.service.axis.RequesterService;
import com.amazonaws.mturk.util.PropertiesClientConfig;

public class createQualification {
	private RequesterService service;

	public createQualification(String propFilename) {
		String propPath = System.getProperty("user.home") + "/.aws/"
				+ propFilename;
		PropertiesClientConfig prop = new PropertiesClientConfig(propPath);
		service = new RequesterService(prop);
	}

	public static void main(String args[]) {
		String propFilename = null;
		if (args[0].equalsIgnoreCase("-live")) {
			propFilename = "mturk_live.properties";
		} else if (args[0].equalsIgnoreCase("-sandbox")) {
			propFilename = "mturk_sandbox.properties";
		} else {
			System.out.println("Incorrect environment name.");
			System.exit(0);
		}
		createQualification createQualification = new createQualification(
				propFilename);
		createQualification.createQualificationTask();
	}

	public void createQualificationTask() {
		String questionXML = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
				+ "<QuestionForm xmlns=\"http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd\">"
				+ "<Overview><Title>Qualification Test For Eye-Hair Annotation</Title></Overview>"
				+ " <Question><QuestionIdentifier>question1</QuestionIdentifier><QuestionContent>"
				+ "<Text> 1.Please open this web site in a new browser window:	https://s3-us-west-2.amazonaws.com/aisoftwareresearch/Qualification/qualification_test.html"
				+ "\n 2. Read and follow the instructions there. \n 3. After completing the task, paste the confirmation code below. </Text>"
				+ "	</QuestionContent><AnswerSpecification><FreeTextAnswer>"
				+"<Constraints> <Length minLength=\"3\" /> <AnswerFormatRegex regex=\"\\S\" errorText=\"The content cannot be blank.\"/> </Constraints>"
				+ "</FreeTextAnswer></AnswerSpecification></Question></QuestionForm>";
		long timeout = 3600;
		long retry = 30;
		/* A new name should be given for each qualification */
		String name = "AI Software Research: Eye Hair Annotation";
		String keywords = "eye hair";
		String description = "custom qualification for eye hair annotation";
		/* parameters answerKey and auto-grant are set to null. */
		QualificationType customQualification = service
				.createQualificationType(name, keywords, description,
						QualificationTypeStatus.Active, retry, questionXML,
						null, timeout, false, null);
		service.getAllQualificationRequests(null);
		System.out.println("Qualifcation ID:	"
				+ customQualification.getQualificationTypeId());

	}

}
