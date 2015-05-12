package edu.isi.dig.mturk;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import com.amazonaws.mturk.addon.BatchItemCallback;
import com.amazonaws.mturk.addon.HITDataBuffer;
import com.amazonaws.mturk.addon.HITDataInput;
import com.amazonaws.mturk.addon.HITResults;
import com.amazonaws.mturk.requester.Assignment;
import com.amazonaws.mturk.service.axis.RequesterService;
import com.amazonaws.mturk.util.PropertiesClientConfig;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ListObjectsRequest;
import com.amazonaws.services.s3.model.ObjectListing;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectSummary;

public class hitResults {
	private RequesterService service;
	String successFile = "", fileContent = "";
	private String bucketName = "", prefixKey = "";
	private AmazonS3 s3client;
	private static String propFilename = "";

	public hitResults(String bucketName, String propFilename) {
		this.bucketName = "aisoftwareresearch/ner/" + bucketName + "/hits";
		this.prefixKey = "ner/" + bucketName + "/hits";
		s3client = hitFiles.ConnectToAWS(propFilename);

		String propPath = System.getProperty("user.home") + "/.aws/"
				+ propFilename;
		PropertiesClientConfig prop = new PropertiesClientConfig(propPath);
		service = new RequesterService(prop);
	}

	public void getAllHits() {
		ArrayList<String> hitIds = new ArrayList<String>();
		ArrayList<String> folderNames = new ArrayList<String>();
		String line, cvsSplitBy = "\t";
		String mainBucket = "aisoftwareresearch";
		try {
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							if (keyParts.length == 1) {
								folderNames.add(keyParts[0]);
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());
			Iterator<String> folderIter = folderNames.iterator();
			while (folderIter.hasNext()) {
				String currFileName = folderIter.next();
				successFile = currFileName + "/" + currFileName + ".success";
				S3Object in_object = s3client.getObject(new GetObjectRequest(
						bucketName, successFile));
				InputStream in_objectData = in_object.getObjectContent();
				BufferedReader in_reader = new BufferedReader(
						new InputStreamReader(in_objectData));
				while ((line = in_reader.readLine()) != null) {
					String[] content = line.split(cvsSplitBy);
					content[0] = content[0].replace("\"", "");
					if (!content[0].equalsIgnoreCase("hitid")
							&& !hitIds.contains(content[0])
							&& content[0].length() > 0) {
						hitIds.add(content[0]);
					}
				}
				in_object.close();
				in_objectData.close();
				in_reader.close();
			}

			approveAssignments(hitIds);
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	public void approveAssignments(ArrayList<String> hitIds) {
		Assignment[] assignment = null;
		String defaultFeedback = "default feedback";
		try {

			if (hitIds == null) {
				throw new Exception("No hits found");
			} else {
				Iterator<String> iterator = hitIds.iterator();
				while (iterator.hasNext()) {
					String Id = iterator.next();
					assignment = service.getAllSubmittedAssignmentsForHIT(Id);

					if (assignment == null) {
						throw new Exception("No assignments found");
					} else {
						String[] assignmentIds = new String[assignment.length];
						String[] requesterFeedback = new String[assignment.length];
						for (int j = 0; j < assignment.length; j++) {
							requesterFeedback[j] = "approved via java api";
							assignmentIds[j] = assignment[j].getAssignmentId()
									.toString();
						}

						service.approveAssignments(assignmentIds,
								requesterFeedback, defaultFeedback,
								new BatchItemCallback() {
									public void processItemResult(
											Object itemId, boolean succeeded,
											Object result,
											Exception itemException) {
										/*
										 * System.out.println("approved result");
										 * System.out.println("Item id ---" +
										 * itemId);
										 * System.out.println("success bool ---"
										 * + succeeded);
										 * System.out.println(result);
										 */
									}
								});

					}
				}
			}
			getResults();
		} catch (Exception e) {

		}
	}

	public void getResults() {
		String content = "";
		ArrayList<String> folderNames = new ArrayList<String>();
		String mainBucket = "aisoftwareresearch";
		try {

			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							if (keyParts.length == 1) {
								folderNames.add(keyParts[0]);
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());
			Iterator<String> folderIter = folderNames.iterator();
			while (folderIter.hasNext()) {
				String currFileName = folderIter.next();

				successFile = currFileName + "/" + currFileName + ".success";
				HITDataBuffer input_buffer = new HITDataBuffer();
				S3Object in_object = s3client.getObject(new GetObjectRequest(
						bucketName, successFile));
				InputStream in_objectData = in_object.getObjectContent();
				BufferedReader in_reader = new BufferedReader(
						new InputStreamReader(in_objectData));
				while ((content = in_reader.readLine()) != null) {
					input_buffer.writeLine(content.split("\t"));
				}
				HITDataInput input = input_buffer;
				in_object.close();
				in_objectData.close();
				in_reader.close();
				input_buffer.close();
				/* Reset the content for each success file */
				fileContent = "HitId\t WorkerId\tAssignmentId\tSentenceId\tOffset\tHightlighted Text\tCategory\tText\tEncoded Text\n";
				service.getResults(input, new BatchItemCallback() {
					public void processItemResult(Object itemId,
							boolean succeeded, Object result,
							Exception itemException) {
						HITResults hitresult = (HITResults) result;
						Assignment resultassignments[] = hitresult
								.getAssignments();
						Map<String, String> assignmap, hitmap, resultmap;
						resultmap = new HashMap<String, String>();
						for (int j = 0; j < resultassignments.length; j++) {

							hitmap = hitresult.getHITResults();
							assignmap = hitresult
									.getAssignmentResults(resultassignments[j]);
							resultmap.putAll(hitmap);
							resultmap.putAll(assignmap);
							String workerId = resultmap.get("workerid");
							String assignmentid = resultmap.get("assignmentid");
							String hitid = resultmap.get("hitid");
							String[] allAnswers = resultmap.get(
									"answers[question_id answer_value]").split(
									"\n");

							for (String answer : allAnswers) {

								answer = answer.trim();
								/*
								 * Only if answer has content it need to be
								 * written to file. Answer may not have content
								 * because of the design of the radio button
								 * values and splitting result map values by \n.
								 */
								if (answer.length() > 0) {
									/*
									 * Since the first token is the name of
									 * checkbox / radio button it can be trimmed
									 * before writing to file
									 */
									System.out.println(answer);
									String trimValue = answer.split("\t")[0];
									
									fileContent += hitid
											+ "\t"
											+ workerId
											+ "\t"
											+ assignmentid
											+ "\t"
											+ answer.substring(
													trimValue.length())
											+ "\n";
								}
							}
							resultmap.clear();
						}

					}

				});
				fileContent += "\n";
				if (fileContent.length() > 0) {
					String keyName = currFileName + "/" + currFileName + ".tsv";
					InputStream inputStream = new ByteArrayInputStream(
							fileContent.getBytes());
					ObjectMetadata metadata = new ObjectMetadata();
					/*
					 * Set content length. Else stream contents will be buffered
					 * in memory and could result in out of memory errors.
					 */
					//metadata.setContentLength(fileContent.length());
					PutObjectRequest request = new PutObjectRequest(bucketName,
							keyName, inputStream, metadata);
					s3client.putObject(request);
					inputStream.close();
				}

			}
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	public static void main(String args[]) {
		if (args[0].equalsIgnoreCase("-live")) {
			propFilename = "mturk_live.properties";
		} else if (args[0].equalsIgnoreCase("-sandbox")) {
			propFilename = "mturk_sandbox.properties";
		} else {
			System.out.println("Incorrect environment name.");
			System.exit(0);
		}
		if (args[0].equals("-live")) {
			propFilename = "mturk_live.properties";
		} else {
			propFilename = "mturk_sandbox.properties";
		}
		hitResults hitResults = new hitResults(args[1], propFilename);
		hitResults.getAllHits();
	}
}
